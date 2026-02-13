from locust import HttpUser, task, between
from pathlib import Path

class ScanUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def scan_contract(self):
        sol_file = Path(__file__).parent / "contracts" / "simple.sol"

        with sol_file.open("rb") as f:
            files = {
                "file": ("simple.sol", f, "application/octet-stream")
            }

            self.client.post(
                "/api/v1/scan",
                files=files,
                name="/api/v1/scan"
            )
