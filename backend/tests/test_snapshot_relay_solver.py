from backend.cli.snapshot_relay_solver import (
    build_restore_candidate,
    solve_records,
    suggest_flags,
)


def _sample_records():
    jobs = [
        {
            "slug": "bucket-parade",
            "flow": "audit-replay",
            "status": "ready",
            "snapshot_id": "snap-300",
            "queued_at": "2026-04-12T07:40:03Z",
        },
        {
            "slug": "ember-ferry",
            "flow": "prod-restore",
            "status": "suppressed",
            "snapshot_id": "snap-301",
            "queued_at": "2026-04-12T07:41:17Z",
        },
        {
            "slug": "cobalt-span",
            "flow": "prod-restore",
            "status": "ready",
            "snapshot_id": "snap-302",
            "queued_at": "2026-04-12T07:42:29Z",
        },
        {
            "slug": "radial-lake",
            "flow": "prod-restore",
            "status": "queued",
            "snapshot_id": "snap-303",
            "queued_at": "2026-04-12T07:43:42Z",
        },
        {
            "slug": "violet-span",
            "flow": "prod-restore",
            "status": "ready",
            "snapshot_id": "snap-304",
            "queued_at": "2026-04-12T07:44:54Z",
        },
    ]
    snapshots = [
        {
            "id": "snap-300",
            "family_id": "pb",
            "mark_id": "bs",
            "tier": "gold",
            "region": "primary",
            "state": "sealed",
            "fabric": "braided",
        },
        {
            "id": "snap-301",
            "family_id": "ms",
            "mark_id": "fy",
            "tier": "gold",
            "region": "primary",
            "state": "sealed",
            "fabric": "braided",
        },
        {
            "id": "snap-302",
            "family_id": "cb",
            "mark_id": "ce",
            "tier": "gold",
            "region": "primary",
            "state": "sealed",
            "fabric": "woven",
        },
        {
            "id": "snap-303",
            "family_id": "rd",
            "mark_id": "ks",
            "tier": "gold",
            "region": "edge",
            "state": "sealed",
            "fabric": "braided",
        },
        {
            "id": "snap-304",
            "family_id": "em",
            "mark_id": "vt",
            "tier": "gold",
            "region": "primary",
            "state": "sealed",
            "fabric": "braided",
        },
    ]
    leases = [
        {
            "id": "ls-300",
            "job_slug": "bucket-parade",
            "imported_at": "2026-04-12T07:40:04Z",
            "connector": "lease-vault",
            "lane_id": "pd:rs",
            "visibility": "restore",
            "audience": "restore-agent",
            "seal_tag": "mesh-v4",
            "family_id": "pb",
            "mark_id": "bs",
        },
        {
            "id": "ls-301",
            "job_slug": "ember-ferry",
            "imported_at": "2026-04-12T07:41:18Z",
            "connector": "lease-vault",
            "lane_id": "pd:rs",
            "visibility": "restore",
            "audience": "restore-agent",
            "seal_tag": "mesh-v4",
            "family_id": "ms",
            "mark_id": "fy",
        },
        {
            "id": "ls-302",
            "job_slug": "cobalt-span",
            "imported_at": "2026-04-12T07:42:30Z",
            "connector": "lease-vault",
            "lane_id": "pd:rs",
            "visibility": "restore",
            "audience": "restore-agent",
            "seal_tag": "mesh-v4",
            "family_id": "cb",
            "mark_id": "ce",
        },
        {
            "id": "ls-303",
            "job_slug": "radial-lake",
            "imported_at": "2026-04-12T07:43:43Z",
            "connector": "lease-vault",
            "lane_id": "pd:rs",
            "visibility": "restore",
            "audience": "restore-agent",
            "seal_tag": "mesh-v4",
            "family_id": "rd",
            "mark_id": "ks",
        },
        {
            "id": "ls-304",
            "job_slug": "violet-span",
            "imported_at": "2026-04-12T07:44:55Z",
            "connector": "lease-vault",
            "lane_id": "pd:rs",
            "visibility": "restore",
            "audience": "restore-agent",
            "seal_tag": "mesh-v4",
            "family_id": "em",
            "mark_id": "vt",
        },
    ]
    controller_log = "\n".join(
        [
            "2026-04-12T07:40:04Z job=bucket-parade event=skip reason=flow_mismatch flow=audit-replay",
            "2026-04-12T07:41:18Z job=ember-ferry event=skip reason=status_inactive status=suppressed",
            "2026-04-12T07:42:31Z job=cobalt-span event=attach_blockers reasons=integrity_mesh",
            "2026-04-12T07:43:44Z job=radial-lake event=attach_blockers reasons=snapshot_region",
            "2026-04-12T07:44:56Z job=violet-span event=attach_candidate reasons=snapshot_ok+lease_ok",
        ]
    )
    return jobs, snapshots, leases, controller_log


def test_solve_bundle_finds_first_trusted_candidate() -> None:
    jobs, snapshots, leases, controller_log = _sample_records()
    result = solve_records(jobs, snapshots, leases, controller_log)

    assert result.candidate.slug == "violet-span"
    assert result.candidate.lane == "prod-restore"
    assert result.candidate.snapshot == "ember-vault"
    assert result.flag_candidates[0] == "ZeroSecure_CTF{violet-span_prod-restore_ember-vault}"
    assert result.verification_line is not None
    assert "event=attach_candidate" in result.verification_line


def test_build_restore_candidate_requires_trusted_snapshot_and_lease() -> None:
    job = {
        "slug": "violet-span",
        "flow": "prod-restore",
        "status": "ready",
        "snapshot_id": "snap-304",
        "queued_at": "2026-04-12T07:44:54Z",
    }
    snapshot = {
        "id": "snap-304",
        "family_id": "em",
        "mark_id": "vt",
        "tier": "gold",
        "region": "primary",
        "state": "sealed",
        "fabric": "braided",
    }
    trusted_lease = {
        "id": "ls-304",
        "job_slug": "violet-span",
        "imported_at": "2026-04-12T07:44:55Z",
        "connector": "lease-vault",
        "lane_id": "pd:rs",
        "visibility": "restore",
        "audience": "restore-agent",
        "seal_tag": "mesh-v4",
        "family_id": "em",
        "mark_id": "vt",
    }
    untrusted_lease = {
        **trusted_lease,
        "connector": "ticket-bridge",
    }

    candidate = build_restore_candidate(job, snapshot, [untrusted_lease, trusted_lease])

    assert candidate is not None
    assert candidate.snapshot == "ember-vault"
    assert suggest_flags(candidate)[0] == "ZeroSecure_CTF{violet-span_prod-restore_ember-vault}"
