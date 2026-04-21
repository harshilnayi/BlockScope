import os
import sys
from pathlib import Path

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_source_rules.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-only")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-not-for-production-use-only")
os.environ.setdefault("RATE_LIMIT_ENABLED", "False")
os.environ.setdefault("LOG_FILE_ENABLED", "False")
os.environ.setdefault("ADMIN_PASSWORD", "testadmin123")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from analysis.source_rules import run_source_rules  # noqa: E402


def test_source_rules_detect_reentrancy_pattern():
    source = """
    pragma solidity ^0.8.20;
    contract Vulnerable {
        mapping(address => uint256) public balances;
        function withdraw() public {
            uint256 balance = balances[msg.sender];
            (bool success, ) = msg.sender.call{value: balance}("");
            require(success, "Transfer failed");
            balances[msg.sender] = 0;
        }
    }
    """

    findings = run_source_rules(source)
    titles = {finding.title for finding in findings}

    assert "Potential Reentrancy" in titles


def test_source_rules_detect_tx_origin_and_selfdestruct():
    source = """
    pragma solidity ^0.8.20;
    contract Risky {
        function destroy(address payable target) public {
            require(tx.origin == msg.sender, "not allowed");
            selfdestruct(target);
        }
    }
    """

    findings = run_source_rules(source)
    titles = {finding.title for finding in findings}

    assert "tx.origin Authentication" in titles
    assert "Dangerous Self-Destruct" in titles
