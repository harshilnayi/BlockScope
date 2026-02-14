from urllib import response
from locust import HttpUser, task, between
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONTRACTS_DIR = BASE_DIR / "contracts"

class ScanUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.simple_contract = CONTRACTS_DIR / "simple.sol"

    @task(3)
    def scan_contract(self):
        """POST /api/v1/scan — primary workload"""
        with self.simple_contract.open("rb") as f:
            files = {"file": ("simple.sol", f, "application/octet-stream")}
            with self.client.post(
                "/api/v1/scan",
                files=files,
                name="/api/v1/scan",
                catch_response=True,
            ) as response:
                if response.status_code not in (200, 202):
                     response.failure(f"Scan failed: {response.status_code}")


    @task(1)
    def list_scans(self):
        """GET /api/v1/scans — secondary workload"""
        with self.client.get(
            "/api/v1/scans",
            name="/api/v1/scans",
            catch_response=True,
        ) as response:
            if response.status_code >= 500:
                response.failure("Server error while listing scans")

