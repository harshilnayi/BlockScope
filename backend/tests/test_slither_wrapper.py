import time
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from analysis.slither_wrapper import SlitherWrapper, _PARSE_CACHE


@pytest.fixture(autouse=True)
def clear_parse_cache():
    SlitherWrapper.clear_parse_cache()
    yield
    SlitherWrapper.clear_parse_cache()


def _make_wrapper(dummy_slither, timeout: float = 1.0) -> SlitherWrapper:
    wrapper = SlitherWrapper(timeout=timeout)
    wrapper._available = True
    wrapper._Slither = dummy_slither
    wrapper.Slither = dummy_slither
    return wrapper


def _write_contract(contents: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".sol",
        delete=False,
        dir=Path(__file__).resolve().parent,
        encoding="utf-8",
    )
    try:
        tmp.write(contents)
        return Path(tmp.name)
    finally:
        tmp.close()


def test_valid_contract_analysis():
    class DummySlither:
        def __init__(self, path):
            self.contracts = []
            self.detectors_results = []

    contract = _write_contract("pragma solidity ^0.8.0; contract A {}")
    wrapper = _make_wrapper(DummySlither)
    try:
        result = wrapper.parse_contract(contract)
        assert result is not None
    finally:
        contract.unlink(missing_ok=True)


def test_missing_file_raises_when_available():
    class DummySlither:
        def __init__(self, path):
            self.contracts = []
            self.detectors_results = []

    wrapper = _make_wrapper(DummySlither)
    with pytest.raises(FileNotFoundError):
        wrapper.parse_contract(Path(__file__).resolve().parent / "missing.sol")


def test_timeout_scenarios():
    class SlowSlither:
        def __init__(self, path):
            time.sleep(0.05)
            self.contracts = []
            self.detectors_results = []

    contract = _write_contract("contract A{}")
    wrapper = _make_wrapper(SlowSlither, timeout=0.01)
    try:
        with pytest.raises(TimeoutError):
            wrapper.parse_contract(contract)
    finally:
        contract.unlink(missing_ok=True)


def test_parse_cache_reuses_same_result():
    calls = {"count": 0}

    class DummySlither:
        def __init__(self, path):
            calls["count"] += 1
            self.contracts = []
            self.detectors_results = [{"check": "reentrancy"}]

    contract = _write_contract("contract A{}")
    wrapper = _make_wrapper(DummySlither)
    try:
        first = wrapper.parse_contract(contract)
        second = wrapper.parse_contract(contract)

        assert first is second
        assert calls["count"] == 1
        assert SlitherWrapper.parse_cache_size() == 1
    finally:
        contract.unlink(missing_ok=True)


def test_clear_parse_cache_returns_count():
    class DummySlither:
        def __init__(self, path):
            self.contracts = []
            self.detectors_results = []

    contract = _write_contract("contract A{}")
    wrapper = _make_wrapper(DummySlither)
    try:
        wrapper.parse_contract(contract)

        assert SlitherWrapper.parse_cache_size() == 1
        assert SlitherWrapper.clear_parse_cache() == 1
        assert SlitherWrapper.parse_cache_size() == 0
    finally:
        contract.unlink(missing_ok=True)


def test_error_handling():
    class DummySlither:
        def __init__(self, path):
            raise RuntimeError("boom")

    contract = _write_contract("contract A{}")
    wrapper = _make_wrapper(DummySlither)
    try:
        with pytest.raises(RuntimeError, match="boom"):
            wrapper.parse_contract(contract)
    finally:
        contract.unlink(missing_ok=True)


def test_internal_cache_object_supports_clear():
    assert hasattr(_PARSE_CACHE, "clear")


def test_real_slither_modules_use_subprocess_timeout_path():
    class DummySlither:
        __module__ = "slither.fake"

        def __init__(self, path):
            self.contracts = []
            self.detectors_results = []

    contract = _write_contract("contract A{}")
    wrapper = _make_wrapper(DummySlither)
    expected = SimpleNamespace(contracts=[], detectors_results=[])

    try:
        with patch.object(wrapper, "_parse_contract_with_subprocess", return_value=expected) as mocked:
            result = wrapper.parse_contract(contract)
        assert mocked.called
        assert result is expected
    finally:
        contract.unlink(missing_ok=True)
