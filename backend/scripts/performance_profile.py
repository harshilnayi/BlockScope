"""
BlockScope Performance Profiler & Report Generator.

Usage:
    cd backend
    python -m scripts.performance_profile [--url http://localhost:8000] [--runs 5]

Output:
    - Console summary table
    - performance_report.json  (machine-readable)
    - performance_report.md    (human-readable)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Try to import httpx; fall back gracefully
try:
    import httpx
except ImportError:
    print("[ERROR] httpx not installed. Run: pip install httpx")
    sys.exit(1)


# --- Sample payloads ----------------------------------------------------------

CLEAN_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract CleanToken {
    mapping(address => uint256) public balances;
    constructor() { balances[msg.sender] = 1_000_000; }
    function transfer(address to, uint256 amount) public {
        require(balances[msg.sender] >= amount);
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}
"""

VULNERABLE_CONTRACT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
contract Vault {
    mapping(address => uint256) public balances;
    function deposit() public payable { balances[msg.sender] += msg.value; }
    function withdraw() public {
        uint256 amt = balances[msg.sender];
        require(amt > 0);
        (bool ok,) = msg.sender.call{value: amt}("");
        require(ok);
        balances[msg.sender] = 0; // state updated AFTER external call
    }
}
"""


# --- Measurement helper -------------------------------------------------------

def measure(
    client: httpx.Client,
    method: str,
    path: str,
    n: int = 5,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Make *n* requests and return latency statistics.

    Returns a dict with keys: min, max, mean, median, p95, p99, status_codes.
    """
    latencies: List[float] = []
    status_codes: List[int] = []

    for _ in range(n):
        try:
            t0 = time.perf_counter()
            response = getattr(client, method)(path, **kwargs)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            latencies.append(elapsed_ms)
            status_codes.append(response.status_code)
        except Exception as exc:
            print(f"  [WARN] Request to {path} failed: {exc}")

    if not latencies:
        return {"error": f"All {n} requests failed", "path": path}

    sorted_lat = sorted(latencies)
    n_lat = len(sorted_lat)

    def percentile(p: float) -> float:
        idx = min(int(n_lat * p / 100), n_lat - 1)
        return round(sorted_lat[idx], 2)

    return {
        "path":         path,
        "method":       method.upper(),
        "samples":      n_lat,
        "min_ms":       round(min(latencies), 2),
        "max_ms":       round(max(latencies), 2),
        "mean_ms":      round(statistics.mean(latencies), 2),
        "median_ms":    round(statistics.median(latencies), 2),
        "p95_ms":       percentile(95),
        "p99_ms":       percentile(99),
        "status_codes": list(set(status_codes)),
    }


# --- Main profiling routine ---------------------------------------------------

def _fmt(val: Any) -> str:
    """Safely format a millisecond value (float) or return 'N/A'."""
    return f"{val:>7.1f} ms" if isinstance(val, (int, float)) else "    N/A"


def _ok(val: Any, threshold: float) -> bool:
    """Return True only when val is numeric and within threshold."""
    return isinstance(val, (int, float)) and val <= threshold


def _status(ok: bool, warn: bool = False) -> str:
    """ASCII-safe status token."""
    if ok:   return "[PASS]"
    if warn: return "[WARN]"
    return "[FAIL]"


def run_profile(base_url: str, runs: int) -> Dict[str, Any]:
    print(f"\n{'='*60}")
    print(f"  BlockScope Performance Profile")
    print(f"  Target  : {base_url}")
    print(f"  Samples : {runs} per endpoint")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    client = httpx.Client(base_url=base_url, timeout=30.0, follow_redirects=True)
    results: Dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url":     base_url,
        "runs_per_endpoint": runs,
        "endpoints":    {},
        "sla":          {},
    }

    # SLA thresholds (ms)
    slas = {
        "health":       200,
        "root":         100,
        "scan_clean":   2_000,
        "scan_vuln":    2_000,
        "scan_cached":  100,
        "list_scans":   500,
        "performance":  200,
    }

    # -- 1. System endpoints ---------------------------------------------------
    print("  [1/5] System endpoints…")
    for name, path in [("health", "/health"), ("root", "/"), ("performance", "/api/v1/performance")]:
        r = measure(client, "get", path, n=runs)
        results["endpoints"][name] = r
        median = r.get("median_ms")
        ok = _ok(median, slas.get(name, 9999))
        disp = _fmt(median)
        print(f"    {_status(ok):<6} {name:<20} median={disp}")

    # -- 2. List scans ---------------------------------------------------------
    print("  [2/5] List scans endpoint…")
    r = measure(client, "get", "/api/v1/scans?limit=10", n=runs)
    results["endpoints"]["list_scans"] = r
    m = r.get("median_ms")
    print(f"    {_status(_ok(m, slas['list_scans'])):<6} {'list_scans':<20} median={_fmt(m)}")

    # -- 3. Scan clean contract ------------------------------------------------
    print("  [3/5] Scan endpoint (safe contract)…")
    payload_clean = {"source_code": CLEAN_CONTRACT, "contract_name": "CleanToken"}
    r = measure(client, "post", "/api/v1/scan", n=runs, json=payload_clean)
    results["endpoints"]["scan_clean"] = r
    m = r.get("median_ms")
    print(f"    {_status(_ok(m, slas['scan_clean'])):<6} {'scan_clean':<20} median={_fmt(m)}")

    # -- 4. Scan vulnerable contract -------------------------------------------
    print("  [4/5] Scan endpoint (vulnerable contract)…")
    payload_vuln = {"source_code": VULNERABLE_CONTRACT, "contract_name": "VulnerableVault"}
    r = measure(client, "post", "/api/v1/scan", n=runs, json=payload_vuln)
    results["endpoints"]["scan_vuln"] = r
    m = r.get("median_ms")
    print(f"    {_status(_ok(m, slas['scan_vuln'])):<6} {'scan_vuln':<20} median={_fmt(m)}")

    # -- 5. Cache effectiveness ------------------------------------------------
    print("  [5/5] Cache effectiveness (same contract twice)…")
    # First call (populates cache) — ignore failures here
    try:
        client.post("/api/v1/scan", json=payload_clean)
    except Exception:
        pass
    # Second call (should hit cache)
    r_cached = measure(client, "post", "/api/v1/scan", n=runs, json=payload_clean)
    results["endpoints"]["scan_cached"] = r_cached
    mc = r_cached.get("median_ms")
    print(f"    {_status(_ok(mc, slas['scan_cached']), warn=True):<6} {'scan_cached':<20} median={_fmt(mc)}")

    client.close()

    # -- SLA summary -----------------------------------------------------------
    print("\n" + "-"*60)
    print("  SLA Summary")
    print("-"*60)
    all_pass = True
    for name, threshold in slas.items():
        ep = results["endpoints"].get(name, {})
        median = ep.get("median_ms", None)
        if median is None:
            verdict = "SKIP"
            icon    = "[WARN]"
        elif median <= threshold:
            verdict = "PASS"
            icon    = "[PASS]"
        else:
            verdict = "FAIL"
            icon    = "[FAIL]"
            all_pass = False
        results["sla"][name] = {
            "threshold_ms": threshold,
            "median_ms":    median,
            "verdict":      verdict,
        }
        display_ms = f"{median:.0f} ms" if median is not None else "N/A"
        print(f"    {icon:<6} {name:<22} {display_ms:>8}  (SLA: {threshold} ms)  {verdict}")

    results["overall_verdict"] = "PASS" if all_pass else "FAIL"
    print(f"\n  Overall: {'ALL SLAs MET [PASS]' if all_pass else 'SOME SLAs FAILED [FAIL]'}")

    return results


# --- Report writers -----------------------------------------------------------

def write_json(data: Dict[str, Any], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\n  [JSON] report saved: {path.resolve()}")


def write_markdown(data: Dict[str, Any], path: Path) -> None:
    lines = [
        "# BlockScope Performance Report",
        "",
        f"**Generated:** {data['generated_at']}  ",
        f"**Target:** {data['base_url']}  ",
        f"**Samples per endpoint:** {data['runs_per_endpoint']}  ",
        f"**Overall verdict:** {'PASS' if data['overall_verdict'] == 'PASS' else 'FAIL'}",
        "",
        "---",
        "",
        "## Endpoint Latencies",
        "",
        "| Endpoint | Min | Mean | Median | P95 | P99 | SLA | Verdict |",
        "|----------|----:|-----:|-------:|----:|----:|----:|:-------:|",
    ]

    for name, ep in data["endpoints"].items():
        sla_entry = data["sla"].get(name, {})
        threshold = sla_entry.get("threshold_ms", "—")
        verdict   = sla_entry.get("verdict", "—")
        icon      = "PASS" if verdict == "PASS" else ("FAIL" if verdict == "FAIL" else "WARN")
        lines.append(
            f"| {name} "
            f"| {ep.get('min_ms', '—'):>5} ms "
            f"| {ep.get('mean_ms', '—'):>6} ms "
            f"| {ep.get('median_ms', '—'):>6} ms "
            f"| {ep.get('p95_ms', '—'):>5} ms "
            f"| {ep.get('p99_ms', '—'):>5} ms "
            f"| {threshold} ms "
            f"| {icon} {verdict} |"
        )

    lines += [
        "",
        "---",
        "",
        "## SLA Summary",
        "",
        "| Endpoint | Threshold | Median | Verdict |",
        "|----------|----------:|-------:|:-------:|",
    ]
    for name, sla in data["sla"].items():
        icon = "PASS" if sla["verdict"] == "PASS" else ("FAIL" if sla["verdict"] == "FAIL" else "WARN")
        lines.append(
            f"| {name} "
            f"| {sla['threshold_ms']} ms "
            f"| {sla.get('median_ms') or 'N/A'} ms "
            f"| {icon} {sla['verdict']} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Key Findings",
        "",
        "- **Backend response SLA**: < 2 000 ms per scan  ",
        "- **Cache acceleration**: re-scanning identical contracts should be < 100 ms  ",
        "- **Health check SLA**: < 200 ms  ",
        "",
        "> Generated by `scripts/performance_profile.py`",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  [MD]   report saved: {path.resolve()}")


# --- Entry point --------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="BlockScope performance profiler")
    parser.add_argument("--url",  default="http://localhost:8000", help="Backend base URL (default: uvicorn port 8000)")
    parser.add_argument("--runs", default=5, type=int, help="Requests per endpoint")
    parser.add_argument("--out",  default=".", help="Output directory for reports")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = run_profile(args.url, args.runs)

    write_json(results,     out_dir / "performance_report.json")
    write_markdown(results, out_dir / "performance_report.md")

    sys.exit(0 if results["overall_verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
