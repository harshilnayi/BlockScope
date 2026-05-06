"""
Wrapper around Slither for AST parsing.

Performance improvements over the original:
  - Timeout protection  - parse_contract() abandons long-running parses after
    a configurable timeout so a pathological contract does not block requests
    indefinitely.
  - Lazy initialization - the heavy ``Slither`` import is deferred to the
    first call, reducing application startup time.
  - Structured logging  - uses the blockscope logger instead of bare print()
    so all output is captured by the rotating file handler and JSON formatter.
  - Result caching      - individual file-level parse results are cached in a
    thread-safe LRU cache to avoid redundant compilation.
"""

from __future__ import annotations

import hashlib
import logging
import multiprocessing
import os
import pickle
import queue
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("blockscope.slither")

_DEFAULT_TIMEOUT: float = float(os.getenv("SLITHER_TIMEOUT", "60"))
_DEFAULT_PARSE_CACHE_SIZE: int = max(1, int(os.getenv("SLITHER_PARSE_CACHE_SIZE", "8")))
_PARSE_WORKERS: int = max(1, int(os.getenv("SLITHER_MAX_CONCURRENT", "2")))


class _ParseCache:
    """Thread-safe in-memory LRU cache for parsed Slither results."""

    def __init__(self, max_size: int) -> None:
        self._max_size = max_size
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            value = self._store.get(key)
            if value is None:
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = value
            if len(self._store) > self._max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug("Evicted Slither parse cache entry %s...", evicted_key[:16])

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def size(self) -> int:
        with self._lock:
            return len(self._store)


_PARSE_CACHE = _ParseCache(_DEFAULT_PARSE_CACHE_SIZE)
_PARSE_EXECUTOR = ThreadPoolExecutor(
    max_workers=_PARSE_WORKERS,
    thread_name_prefix="blockscope-slither",
)


@dataclass
class _SlitherParseResult:
    """Serializable subset of a Slither parse result."""

    detectors_results: list
    contracts: Optional[list]
    contracts_serialized: bool = True


def _can_pickle(value: Any) -> bool:
    try:
        pickle.dumps(value)
        return True
    except Exception:
        return False


def _parse_contract_subprocess(file_path: str, result_queue: Any) -> None:
    """Worker entrypoint that runs Slither in a killable child process."""
    try:
        from slither import Slither

        slither_obj = Slither(file_path)
        detectors_results = getattr(slither_obj, "detectors_results", [])
        contracts = getattr(slither_obj, "contracts", None)
        contracts_serialized = True

        if contracts is not None and not _can_pickle(contracts):
            contracts = None
            contracts_serialized = False

        result_queue.put(
            (
                "ok",
                _SlitherParseResult(
                    detectors_results=detectors_results,
                    contracts=contracts,
                    contracts_serialized=contracts_serialized,
                ),
            )
        )
    except Exception as exc:  # pragma: no cover - exercised via parent path
        result_queue.put(("err", f"{exc.__class__.__name__}: {exc}"))


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
            timeout: Maximum wall-clock seconds to wait for ``parse_contract``.
        """
        self.timeout = timeout
        self._Slither: Optional[Any] = None
        self.Slither: Optional[Any] = None  # Backwards-compatible alias
        self._available: Optional[bool] = None

    @property
    def available(self) -> bool:
        """Return ``True`` if slither-analyzer is importable, probing once."""
        if self._available is None:
            try:
                from slither import Slither
            except ImportError:
                logger.warning(
                    "Slither not installed - static analysis disabled. "
                    "Install with: pip install slither-analyzer"
                )
                self._Slither = None
                self.Slither = None
                self._available = False
            else:
                self._Slither = Slither
                self.Slither = Slither
                self._available = True
                logger.debug("Slither successfully loaded")
        return bool(self._available)

    def parse_contract(self, file_path: str) -> Any:
        """
        Parse a Solidity contract using Slither, with caching + timeout.

        Args:
            file_path: Absolute or relative path to a ``.sol`` file.

        Returns:
            Slither object containing analysis results.

        Raises:
            RuntimeError: Slither is not installed.
            FileNotFoundError: ``file_path`` does not exist.
            TimeoutError: Parse exceeded ``self.timeout`` seconds.
            Exception: Any underlying Slither parse error.
        """
        if not self.available:
            raise RuntimeError(
                "Slither not available. Install with: pip install slither-analyzer"
            )

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Contract file not found: {path}")

        content_hash: Optional[str]
        try:
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            logger.warning("Could not hash '%s': %s", path, exc)
            content_hash = None

        if content_hash:
            cached_result = _PARSE_CACHE.get(content_hash)
            if cached_result is not None:
                logger.debug("Slither parse cache hit for %s", path.name)
                return cached_result

        parser_cls = self._Slither or self.Slither
        if parser_cls is None:
            raise RuntimeError("Slither parser is not initialised")

        logger.debug("Parsing '%s' (timeout=%.1fs)...", path.name, self.timeout)
        started = time.monotonic()
        try:
            if self._should_use_subprocess_timeout(parser_cls):
                slither_obj = self._parse_contract_with_subprocess(path)
            else:
                future = _PARSE_EXECUTOR.submit(parser_cls, str(path))
                try:
                    slither_obj = future.result(timeout=self.timeout)
                except FuturesTimeoutError as exc:
                    future.cancel()
                    logger.error(
                        "Slither parse timed out for '%s' after %.1fs",
                        path.name,
                        self.timeout,
                    )
                    raise TimeoutError(
                        f"Slither parse exceeded timeout ({self.timeout:.1f}s)"
                    ) from exc
        except Exception as exc:
            logger.error("Slither failed to parse '%s': %s", path.name, exc)
            raise

        elapsed = time.monotonic() - started
        logger.info(
            "Slither parsed '%s' in %.2fs",
            path.name,
            elapsed,
            extra={"file": path.name, "duration_s": round(elapsed, 3)},
        )

        if content_hash:
            _PARSE_CACHE.set(content_hash, slither_obj)

        return slither_obj

    def _should_use_subprocess_timeout(self, parser_cls: Any) -> bool:
        """Use a process boundary for real Slither so timeouts can terminate it."""
        parser_module = getattr(parser_cls, "__module__", "")
        return parser_module.startswith("slither")

    def _parse_contract_with_subprocess(self, path: Path) -> _SlitherParseResult:
        """Run a Slither parse in a child process so timeout enforcement is real."""
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue(maxsize=1)
        process = ctx.Process(
            target=_parse_contract_subprocess,
            args=(str(path), result_queue),
            daemon=True,
        )
        process.start()
        process.join(self.timeout)

        if process.is_alive():
            process.terminate()
            process.join(5)
            logger.error(
                "Slither parse timed out for '%s' after %.1fs; child process terminated",
                path.name,
                self.timeout,
            )
            raise TimeoutError(f"Slither parse exceeded timeout ({self.timeout:.1f}s)")

        try:
            status, payload = result_queue.get_nowait()
        except queue.Empty as exc:
            raise RuntimeError(
                f"Slither parse exited without producing a result (exitcode={process.exitcode})"
            ) from exc
        finally:
            result_queue.close()
            result_queue.join_thread()

        if status != "ok":
            raise RuntimeError(str(payload))

        if isinstance(payload, _SlitherParseResult) and not payload.contracts_serialized:
            logger.warning(
                "Slither contracts for '%s' could not be serialized across the timeout process boundary; "
                "AST-backed rule analysis will be unavailable for this parse",
                path.name,
            )

        return payload

    def get_ast_nodes(self, slither_obj: Any) -> Optional[list]:
        """Return contract nodes from a parsed Slither object."""
        if not slither_obj:
            return None
        return slither_obj.contracts

    @staticmethod
    def clear_parse_cache() -> int:
        """Evict all cached parse results and return the number cleared."""
        count = _PARSE_CACHE.clear()
        logger.info("Slither parse cache cleared (%d entries)", count)
        return count

    @staticmethod
    def parse_cache_size() -> int:
        """Return the number of cached parse results."""
        return _PARSE_CACHE.size()

    def __repr__(self) -> str:
        return (
            f"SlitherWrapper(available={self._available!r}, "
            f"timeout={self.timeout}s, "
            f"cached_parses={self.parse_cache_size()})"
        )
