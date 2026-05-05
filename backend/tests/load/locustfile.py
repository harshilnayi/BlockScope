"""
BlockScope Load Test — Locust configuration
============================================
Usage (from repo root):
    locust -f backend/tests/load/locustfile.py --host http://localhost:8000

Or with a preset conf:
    locust -f backend/tests/load/locustfile.py --config backend/tests/load/locust.conf
"""

from locust import HttpUser, between, task
from pathlib import Path

CONTRACT_DIR = Path(__file__).parent / "contracts"

CONTRACTS = {
    "small": CONTRACT_DIR / "small.sol",
    "medium": CONTRACT_DIR / "medium.sol",
    "large": CONTRACT_DIR / "large.sol",
}


class ScanUser(HttpUser):
    """Simulates a user submitting Solidity contracts for security analysis."""

    wait_time = between(1, 2)

    # ------------------------------------------------------------------ #
    # Write tasks — POST to the file-upload endpoint                      #
    # ------------------------------------------------------------------ #

    @task(3)
    def scan_small_contract(self):
        """Upload a small contract (highest frequency — most common case)."""
        self._scan_contract("small")

    @task(2)
    def scan_medium_contract(self):
        """Upload a medium contract."""
        self._scan_contract("medium")

    @task(1)
    def scan_large_contract(self):
        """Upload a large contract (least frequent — most expensive)."""
        self._scan_contract("large")

    # ------------------------------------------------------------------ #
    # Read tasks — realistic mixed read/write ratio                       #
    # ------------------------------------------------------------------ #

    @task(4)
    def list_recent_scans(self):
        """Fetch the most recent 10 scan results (common dashboard call)."""
        self.client.get(
            "/api/v1/scans",
            params={"skip": 0, "limit": 10},
            name="/api/v1/scans (list)",
        )

    @task(2)
    def health_check(self):
        """Poll the health endpoint (used by load-balancer probes)."""
        self.client.get("/health", name="/health")

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _scan_contract(self, size: str) -> None:
        """POST a .sol file to the *file upload* endpoint (not the JSON endpoint)."""
        sol_file = CONTRACTS[size]
        if not sol_file.exists():
            # Gracefully skip if the fixture contract is missing in the environment
            return

        with sol_file.open("rb") as f:
            self.client.post(
                "/api/v1/scan/file",          # ← correct file-upload endpoint
                files={"file": (sol_file.name, f, "text/plain")},
                name=f"/api/v1/scan/file ({size})",
            )
