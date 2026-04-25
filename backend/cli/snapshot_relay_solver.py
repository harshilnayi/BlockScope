from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import ZipFile


ACTIVE_STATUSES = {"queued", "ready"}
RESTORE_FLOW = "prod-restore"
TRUSTED_CONNECTORS = {"lease-vault"}
TRUSTED_LANE_ID = "pd:rs"

FAMILY_WORDS = {
    "pb": "public",
    "ms": "mist",
    "cb": "cobalt",
    "rd": "radial",
    "em": "ember",
    "sv": "silver",
}

MARK_WORDS = {
    "bs": "basin",
    "fy": "ferry",
    "ce": "cache",
    "ks": "keystone",
    "vt": "vault",
    "rd": "rind",
}

LANE_HEAD = {
    "pd": "prod",
    "rv": "review",
}

LANE_TAIL = {
    "rs": "restore",
    "ds": "dispatch",
}


@dataclass(frozen=True)
class RestoreCandidate:
    slug: str
    lane: str
    snapshot: str
    lease_alias: str


@dataclass(frozen=True)
class JobAssessment:
    slug: str
    outcome: str
    detail: str


@dataclass(frozen=True)
class SolveResult:
    candidate: RestoreCandidate
    assessments: list[JobAssessment]
    flag_candidates: list[str]
    verification_line: str | None


def decode_snapshot_alias(entry: dict[str, Any]) -> str | None:
    left = FAMILY_WORDS.get(entry.get("family_id"))
    right = MARK_WORDS.get(entry.get("mark_id"))
    if not left or not right:
        return None
    return f"{left}-{right}"


def decode_lane(lane_id: str | None) -> str:
    head, _, tail = str(lane_id or "").partition(":")
    if head not in LANE_HEAD or tail not in LANE_TAIL:
        return "review-dispatch"
    return f"{LANE_HEAD[head]}-{LANE_TAIL[tail]}"


def eligible_job(job: dict[str, Any]) -> bool:
    return job.get("flow") == RESTORE_FLOW and job.get("status") in ACTIVE_STATUSES


def is_trusted_lease(entry: dict[str, Any]) -> bool:
    return (
        entry.get("connector") in TRUSTED_CONNECTORS
        and entry.get("visibility") == "restore"
        and entry.get("audience") == "restore-agent"
        and entry.get("lane_id") == TRUSTED_LANE_ID
        and entry.get("seal_tag") == "mesh-v4"
    )


def normalize_lease(entry: dict[str, Any]) -> dict[str, Any]:
    alias = decode_snapshot_alias(entry)
    return {
        "id": entry.get("id"),
        "alias": alias,
        "lane": decode_lane(entry.get("lane_id")),
        "promoted": is_trusted_lease(entry) and alias is not None,
    }


def sort_by_time(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    return sorted(items, key=lambda entry: entry[key])


def build_restore_candidate(
    job: dict[str, Any],
    snapshot: dict[str, Any] | None,
    leases: list[dict[str, Any]],
) -> RestoreCandidate | None:
    if not eligible_job(job):
        return None

    if not snapshot:
        return None

    if snapshot.get("tier") != "gold":
        return None
    if snapshot.get("region") != "primary":
        return None
    if snapshot.get("state") != "sealed":
        return None
    if snapshot.get("fabric") != "braided":
        return None

    promoted = [
        normalize_lease(entry)
        for entry in sort_by_time(
            [entry for entry in leases if entry.get("job_slug") == job.get("slug")],
            "imported_at",
        )
    ]
    promoted = [entry for entry in promoted if entry["promoted"]]

    snapshot_alias = decode_snapshot_alias(snapshot)
    if not promoted or not snapshot_alias:
        return None

    return RestoreCandidate(
        slug=job["slug"],
        lane=promoted[0]["lane"],
        snapshot=snapshot_alias,
        lease_alias=promoted[0]["alias"],
    )


def assess_job(
    job: dict[str, Any],
    snapshots_by_id: dict[str, dict[str, Any]],
    leases: list[dict[str, Any]],
) -> JobAssessment:
    if job.get("flow") != RESTORE_FLOW:
        return JobAssessment(job["slug"], "rejected", "flow_mismatch")
    if job.get("status") not in ACTIVE_STATUSES:
        return JobAssessment(job["slug"], "rejected", f"status_inactive:{job.get('status')}")

    snapshot = snapshots_by_id.get(job.get("snapshot_id"))
    if not snapshot:
        return JobAssessment(job["slug"], "rejected", "snapshot_missing")
    if snapshot.get("tier") != "gold":
        return JobAssessment(job["slug"], "rejected", "snapshot_tier")
    if snapshot.get("region") != "primary":
        return JobAssessment(job["slug"], "rejected", "snapshot_region")
    if snapshot.get("state") != "sealed":
        return JobAssessment(job["slug"], "rejected", "snapshot_state")
    if snapshot.get("fabric") != "braided":
        return JobAssessment(job["slug"], "rejected", "integrity_mesh")

    job_leases = [
        entry
        for entry in sort_by_time(
            [entry for entry in leases if entry.get("job_slug") == job.get("slug")],
            "imported_at",
        )
        if normalize_lease(entry)["promoted"]
    ]
    if not job_leases:
        return JobAssessment(job["slug"], "rejected", "lease_untrusted")

    snapshot_alias = decode_snapshot_alias(snapshot)
    if not snapshot_alias:
        return JobAssessment(job["slug"], "rejected", "snapshot_alias_invalid")

    return JobAssessment(job["slug"], "candidate", "snapshot_ok+lease_ok")


def suggest_flags(candidate: RestoreCandidate) -> list[str]:
    return [
        f"ZeroSecure_CTF{{{candidate.slug}_{candidate.lane}_{candidate.snapshot}}}",
        f"ZeroSecure_CTF{{{candidate.slug}:{candidate.lane}:{candidate.snapshot}}}",
        f"ZeroSecure_CTF{{{candidate.lane}_{candidate.snapshot}}}",
        f"ZeroSecure_CTF{{{candidate.slug}_{candidate.snapshot}}}",
    ]


def _read_text(bundle_path: Path, suffix: str) -> str:
    with ZipFile(bundle_path) as archive:
        for name in archive.namelist():
            if name.endswith(suffix):
                return archive.read(name).decode("utf-8")
    raise FileNotFoundError(f"Bundle entry not found: {suffix}")


def load_bundle(bundle_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    jobs = json.loads(_read_text(bundle_path, "artifacts/jobs.json"))
    snapshots = json.loads(_read_text(bundle_path, "artifacts/snapshots.json"))
    leases = [
        json.loads(line)
        for line in _read_text(bundle_path, "artifacts/leases.ndjson").splitlines()
        if line.strip()
    ]
    controller_log = _read_text(bundle_path, "artifacts/controller.log")
    return jobs, snapshots, leases, controller_log


def solve_bundle(bundle_path: Path) -> SolveResult:
    jobs, snapshots, leases, controller_log = load_bundle(bundle_path)
    return solve_records(jobs, snapshots, leases, controller_log)


def solve_records(
    jobs: list[dict[str, Any]],
    snapshots: list[dict[str, Any]],
    leases: list[dict[str, Any]],
    controller_log: str,
) -> SolveResult:
    snapshots_by_id = {snapshot["id"]: snapshot for snapshot in snapshots}
    assessments = [
        assess_job(job, snapshots_by_id, leases) for job in sort_by_time(jobs, "queued_at")
    ]

    candidate: RestoreCandidate | None = None
    for job in sort_by_time(jobs, "queued_at"):
        candidate = build_restore_candidate(job, snapshots_by_id.get(job["snapshot_id"]), leases)
        if candidate:
            break

    if not candidate:
        raise ValueError("No trusted production snapshot could be attached from this bundle.")

    verification_line = next(
        (
            line
            for line in controller_log.splitlines()
            if f"job={candidate.slug}" in line and "event=attach_candidate" in line
        ),
        None,
    )

    return SolveResult(
        candidate=candidate,
        assessments=assessments,
        flag_candidates=suggest_flags(candidate),
        verification_line=verification_line,
    )


def format_result(result: SolveResult) -> str:
    lines = [
        "Snapshot Relay solve result",
        f"first_valid_job: {result.candidate.slug}",
        f"trusted_lease_lane: {result.candidate.lane}",
        f"restored_snapshot_codename: {result.candidate.snapshot}",
        f"recommended_flag: {result.flag_candidates[0]}",
        "",
        "job_assessment:",
    ]
    lines.extend(f"  - {item.slug}: {item.outcome} ({item.detail})" for item in result.assessments)
    lines.append("")
    lines.append("flag_candidates:")
    lines.extend(f"  - {flag}" for flag in result.flag_candidates)
    if result.verification_line:
        lines.append("")
        lines.append(f"verification_log: {result.verification_line}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recover the first trusted production snapshot from a Snapshot Relay challenge bundle."
    )
    parser.add_argument("bundle", type=Path, help="Path to the Snapshot Relay ZIP bundle")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of formatted text",
    )
    args = parser.parse_args(argv)

    result = solve_bundle(args.bundle)
    if args.json:
        print(
            json.dumps(
                {
                    "first_valid_job": result.candidate.slug,
                    "trusted_lease_lane": result.candidate.lane,
                    "restored_snapshot_codename": result.candidate.snapshot,
                    "flag_candidates": result.flag_candidates,
                    "verification_log": result.verification_line,
                },
                indent=2,
            )
        )
    else:
        print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
