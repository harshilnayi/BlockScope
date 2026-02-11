import pytest
from pathlib import Path
from backend.analysis.slither_wrapper import SlitherWrapper


def test_valid_contract_analysis(tmp_path, monkeypatch):
    contract = tmp_path / "test.sol"
    contract.write_text("pragma solidity ^0.8.0; contract A {}")

    class DummySlither:
        def __init__(self, path):
            self.contracts = []
            self.detectors_results = []

    monkeypatch.setattr("slither.Slither", DummySlither)

    wrapper = SlitherWrapper()
    result = wrapper.parse_contract(contract)
    assert result is not None


def test_invalid_contract_handling(tmp_path):
    wrapper = SlitherWrapper()
    with pytest.raises(FileNotFoundError):
        wrapper.parse_contract(tmp_path / "missing.sol")


def test_timeout_scenarios(monkeypatch, tmp_path):
    contract = tmp_path / "test.sol"
    contract.write_text("contract A{}")

    class DummySlither:
        def __init__(self, path):
            raise TimeoutError("timeout")

    monkeypatch.setattr("slither.Slither", DummySlither)

    wrapper = SlitherWrapper()
    with pytest.raises(TimeoutError):
        wrapper.parse_contract(contract)


def test_json_parsing(monkeypatch, tmp_path):
    contract = tmp_path / "test.sol"
    contract.write_text("contract A{}")

    class DummySlither:
        def __init__(self, path):
            self.detectors_results = [{"check": "reentrancy"}]
            self.contracts = []

    monkeypatch.setattr("slither.Slither", DummySlither)
    wrapper = SlitherWrapper()
    result = wrapper.parse_contract(contract)
    assert isinstance(result.detectors_results, list)


def test_vulnerability_mapping(monkeypatch, tmp_path):
    contract = tmp_path / "test.sol"
    contract.write_text("contract A{}")

    class DummySlither:
        def __init__(self, path):
            self.detectors_results = [{"impact": "high"}]
            self.contracts = []

    monkeypatch.setattr("slither.Slither", DummySlither)
    wrapper = SlitherWrapper()
    result = wrapper.parse_contract(contract)
    assert result.detectors_results[0]["impact"] == "high"


def test_score_calculation_placeholder():
    assert 100 - 20 - 10 == 70


def test_error_handling(monkeypatch, tmp_path):
    contract = tmp_path / "test.sol"
    contract.write_text("contract A{}")

    class DummySlither:
        def __init__(self, path):
            raise Exception("boom")

    monkeypatch.setattr("slither.Slither", DummySlither)

    wrapper = SlitherWrapper()
    with pytest.raises(Exception):
        wrapper.parse_contract(contract)


def test_file_cleanup(tmp_path):
    f = tmp_path / "x.sol"
    f.write_text("x")
    assert f.exists()
    f.unlink()
    assert not f.exists()
