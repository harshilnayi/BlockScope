from locust import HttpUser, task, between
from pathlib import Path

CONTRACT_DIR = Path(__file__).parent / "contracts"

CONTRACTS = {
    "small": CONTRACT_DIR / "small.sol",
    "medium": CONTRACT_DIR / "medium.sol",
    "large": CONTRACT_DIR / "large.sol",
}

class ScanUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def scan_small_contract(self):
        self._scan_contract("small")

    @task(2)
    def scan_medium_contract(self):
        self._scan_contract("medium")

    @task(1)
    def scan_large_contract(self):
        self._scan_contract("large")

    def _scan_contract(self, size):
        sol_file = CONTRACTS[size]

        with sol_file.open("rb") as f:
            files = {
                "file": (sol_file.name, f, "application/octet-stream")
            }
            self.client.post(
                "/api/v1/scan",
                files=files,
                name=f"/api/v1/scan ({size})"
            )
