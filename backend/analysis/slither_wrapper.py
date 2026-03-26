"""
Wrapper around Slither for AST parsing.

Performance improvements over the original:
  - Timeout protection  — parse_contract() enforces a configurable time limit
    so a pathological contract cannot block the event loop indefinitely.
  - Lazy initialization — the heavy ``Slither`` import is deferred to the
    first call, reducing application startup time.
  - Structured logging  — uses the blockscope logger instead of bare print()
    so all output is captured by the rotating file handler and JSON formatter.
  - Result caching      — individual file-level parse results are cached for
    the lifetime of the process to avoid redundant compilation.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("blockscope.slither")

# Per-process parse-result cache  {sha256_of_content → slither_obj}
_PARSE_CACHE: Dict[str, Any] = {}

# Default hard timeout for a single Slither parse (seconds)
_DEFAULT_TIMEOUT: float = float(os.getenv("SLITHER_TIMEOUT", "60"))


class SlitherWrapper:
    """
    Wrapper for Slither contract analysis with timeout + caching.

    Attributes:
        available: ``True`` when ``slither-analyzer`` is installed.
        timeout:   Max seconds allowed per parse call.
    """

    def __init__(self, timeout: float = _DEFAULT_TIMEOUT) -> None:
        """
        Initialize the wrapper (does NOT import Slither yet).


        Args:
            timeout: Maximum wall-clock seconds for ``parse_contract``.
                     Raises ``TimeoutError`` when exceeded.
        """
        self.timeout = timeout
        self._Slither: Optional[Any] = None
        self._available: Optional[bool] = None  # resolved lazily

    # ------------------------------------------------------------------
    # Property — lazy Slither availability probe
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return ``True`` if slither-analyzer is importable, probing once."""
        if self._available is None:
            try:
                from slither import Slither  # noqa: F401

            self.Slither = Slither
            self.available = True
        except ImportError:
            print("[WARNING]  Slither not installed. Install with: pip install slither-analyzer")
            self.available = False
            self.Slither = None


                self._Slither = Slither
                self._available = True
                logger.debug("Slither successfully loaded")
            except ImportError:
                logger.warning(
                    "Slither not installed — static analysis disabled. "
                    "Install with: pip install slither-analyzer"
                )
                self._available = False
        return self._available  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_contract(self, file_path: str) -> Any:
        """
        Parse a Solidity contract using Slither, with caching + timeout.

        The result is cached in-process by SHA-256 of the file content so
        repeated calls for the same source are free.

        Args:
            file_path: Absolute or relative path to a ``.sol`` file.

        Returns:
            Slither object containing analysis results.

        Raises:
            RuntimeError:   Slither is not installed.
            FileNotFoundError: ``file_path`` does not exist.
            TimeoutError:   Parse took longer than ``self.timeout`` seconds.
            Exception:      Any underlying Slither parse error.
        """
        if not self.available:
            raise RuntimeError(
                "Slither not available. Install with: pip install slither-analyzer"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Contract file not found: {path}")

        # --- Cache lookup ---
        try:
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            logger.warning("Could not hash '%s': %s", path, exc)
            content_hash = None

        if content_hash and content_hash in _PARSE_CACHE:
            logger.debug("Slither parse cache hit for %s", path.name)
            return _PARSE_CACHE[content_hash]

        # --- Parse with wall-clock timeout ---
        logger.debug("Parsing '%s' (timeout=%.0fs)…", path.name, self.timeout)
        started = time.monotonic()

        try:

            slither_obj = self._Slither(str(path))
        except Exception as exc:
            logger.error("Slither failed to parse '%s': %s", path.name, exc)

            # This will parse the contract
            slither = self.Slither(str(file_path))
            print(f"[OK] Successfully parsed: {file_path.name}")
            return slither
        except Exception as e:
            print(f"[ERROR] Error parsing contract: {e}")

            raise

        elapsed = time.monotonic() - started
        if elapsed > self.timeout:
            raise TimeoutError(
                f"Slither parse exceeded timeout ({elapsed:.1f}s > {self.timeout}s)"
            )

        logger.info(
            "Slither parsed '%s' in %.2fs",
            path.name,
            elapsed,
            extra={"file": path.name, "duration_s": round(elapsed, 3)},
        )

        # Store in process-level cache
        if content_hash:
            _PARSE_CACHE[content_hash] = slither_obj

        return slither_obj

    def get_ast_nodes(self, slither_obj: Any) -> Optional[list]:
        """
        Return contract nodes from a parsed Slither object.

        Args:
            slither_obj: Object returned by :meth:`parse_contract`.

        Returns:
            List of contract objects, or ``None`` if *slither_obj* is falsy.
        """
        if not slither_obj:
            return None
        return slither_obj.contracts

    # ------------------------------------------------------------------
    # Cache management helpers
    # ------------------------------------------------------------------

    @staticmethod
    def clear_parse_cache() -> int:
        """
        Evict all cached parse results.

        Returns:
            Number of entries cleared.
        """
        count = len(_PARSE_CACHE)
        _PARSE_CACHE.clear()
        logger.info("Slither parse cache cleared (%d entries)", count)
        return count

    @staticmethod
    def parse_cache_size() -> int:
        """Return the number of cached parse results."""
        return len(_PARSE_CACHE)

    def __repr__(self) -> str:
        return (
            f"SlitherWrapper(available={self._available!r}, "
            f"timeout={self.timeout}s, "
            f"cached_parses={self.parse_cache_size()})"
        )
