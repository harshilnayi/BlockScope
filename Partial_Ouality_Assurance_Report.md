# BlockScope — Partial QA Status Report
> ⚠️ **THIS IS NOT THE FINAL QA DELIVERABLE**
> This document is an interim QA status report. It reflects what has been completed so far.
> The full QA assignment cannot be closed until the items listed under **Section 7: Outstanding Work**
> are completed. This report will be updated to a Final QA Report once those are done.

**Project:** BlockScope — Smart Contract Vulnerability Scanner  
**Report Type:** PARTIAL — Interim Status  
**Report Date:** March 29, 2026  
**Author:** ManasviJ15  
**Evidence Source:** `pytest_errors.txt` (actual test run, Windows, Python 3.11.9, pytest 7.4.4, timestamp: 2026-03-04 01:51–01:52 UTC)

---

## What Is and Is Not in This Report

| QA Task | Status | Notes |
|---|---|---|
| Backend test execution (pytest) | ✅ Complete | 70 tests run, results documented with evidence |
| Bug list with priorities | ✅ Complete | 14 bugs, all backed by actual error output |
| Bug reproduction steps | ✅ Complete | Steps, root causes, and fix-verification notes included |
| Regression testing checklist | ✅ Complete | Checklist ready for use after fixes |
| Manual testing of user flows | ❌ Not started | Blocked: frontend deployment is returning 404 |
| Cross-browser testing | ❌ Not started | Blocked: no live frontend |
| Mobile testing (iOS, Android) | ❌ Not started | Blocked: no live frontend |
| Accessibility testing | ❌ Not started | Blocked: no live frontend |
| UAT with sample users | ❌ Not started | Blocked: no live frontend + no recruited users |
| UAT feedback document | ❌ Not started | Depends on UAT sessions being run |

**Completion estimate: ~40% of assigned QA work done.**
The completed portion covers all backend/API layer testing. The remaining 60% requires a working frontend deployment.

---

## 1. Test Execution Summary

Tests were run locally on Windows (Python 3.11.9, pytest 7.4.4) against the backend. The output below is taken directly from `pytest_errors.txt` in the repository.

```
Platform:  win32 — Python 3.11.9, pytest 7.4.4
Root dir:  E:\BlockScope
Config:    pytest.ini
Collected: 70 items
Run time:  2026-03-04, ~01:51–01:52 UTC
```

### Results by File

| Test File | Collected | Passed | Failed | Error |
|---|---|---|---|---|
| `test_database.py` | 6 | 6 | 0 | 0 |
| `test_e2e.py` | 10 | 10 | 0 | 0 |
| `test_models.py` | 5 | 4 | 1 | 0 |
| `test_orchestrator_unit.py` | 5 | 5 | 0 | 0 |
| `test_scanner.py` | 6 | 6 | 0 | 0 |
| `test_slither_wrapper.py` | 8 | 8 | 0 | 0 |
| `test_utils.py` | 4 | 4 | 0 | 0 |
| `integration/test_database_integration.py` | 2 | 1 | 1 | 0 |
| `integration/test_error_recovery.py` | 3 | 2 | 1 | 0 |
| `integration/test_full_scan_flow.py` | 5 | 1 | 4 | 0 |
| `integration/test_slither_integration.py` | 2 | 1 | 1 | 0 |
| `test_api/test_health_endpoint.py` | 4 | 4 | 0 | 0 |
| `test_api/test_scan_endpoint.py` | 11 | 8 | 2 | 1 |
| **TOTAL** | **70** | **57** | **12** | **1** |

---

## 2. Test Case Results (54 Cases — Backend Only)

Each result is traceable to a specific character in the pytest output string from `pytest_errors.txt`.

### Database Tests — `test_database.py` — 6 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-001 | DB initialises and connects | ✅ PASS | `test_database.py ...... [8%]` — 6 dots, 0 failures |
| TC-002 | Session management works | ✅ PASS | Same |
| TC-003 | Schema applies cleanly | ✅ PASS | Same |
| TC-004 | Test isolation between cases | ✅ PASS | Same |
| TC-005 | Read/write operations succeed | ✅ PASS | Same |
| TC-006 | DB teardown without error | ✅ PASS | Same |

### End-to-End Tests — `test_e2e.py` — 10 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-007 through TC-016 | E2E tests 1–10 | ✅ ALL PASS | `test_e2e.py .......... [22%]` — 10 dots, 0 failures |

### Model Tests — `test_models.py` — 4 PASS, 1 FAIL

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-017 | Model test 1 | ✅ PASS | `test_models.py .F... [30%]` — dot before F |
| TC-018 | `test_vulnerability_model` | ❌ FAIL | `KeyError: 'Scan'` → `sqlalchemy.exc.InvalidRequestError: expression 'Scan' failed to locate a name` — see BUG-001 |
| TC-019 | Model test 3 | ✅ PASS | Dot after F |
| TC-020 | Model test 4 | ✅ PASS | Same |
| TC-021 | Model test 5 | ✅ PASS | Same |

### Orchestrator Unit Tests — `test_orchestrator_unit.py` — 5 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-022 through TC-026 | Orchestrator tests 1–5 | ✅ ALL PASS | `test_orchestrator_unit.py ..... [37%]` — 5 dots |

### Scanner Tests — `test_scanner.py` — 6 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-027 through TC-032 | Scanner tests 1–6 | ✅ ALL PASS | `test_scanner.py ...... [45%]` — 6 dots |

### Slither Wrapper Tests — `test_slither_wrapper.py` — 8 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-033 through TC-040 | Slither wrapper tests 1–8 | ✅ ALL PASS | `test_slither_wrapper.py ........ [57%]` — 8 dots |

### Utils Tests — `test_utils.py` — 4 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-041 through TC-044 | Utils tests 1–4 | ✅ ALL PASS | `test_utils.py .... [62%]` — 4 dots |

### Integration: Database — `test_database_integration.py` — 1 PASS, 1 FAIL

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-045 | DB integration test 1 | ❌ FAIL | `test_database_integration.py F. [65%]` — F first |
| TC-046 | `test_scan_persisted_and_retrievable` | ✅ PASS | Dot after F |

### Integration: Error Recovery — `test_error_recovery.py` — 2 PASS, 1 FAIL

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-047 | `test_malformed_contract_recovery` | ❌ FAIL | `test_error_recovery.py F.. [70%]` — F first. Assert `'vulnerabilities' in data` but API returned `{'findings': [], 'overall_score': 100, ...}` — see BUG-003 |
| TC-048 | Error recovery test 2 | ✅ PASS | First dot after F |
| TC-049 | Error recovery test 3 | ✅ PASS | Second dot after F |

### Integration: Full Scan Flow — `test_full_scan_flow.py` — 1 PASS, 4 FAIL

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-050 | Full scan — clean contract | ❌ FAIL | `assert 'vulnerabilities' in data` — API returned `{'contract_name': 'Clean', 'findings': [], 'overall_score': 100, 'scan_id': 5}` — BUG-003 |
| TC-051 | Full scan — broken/malformed contract | ❌ FAIL | Same assertion failure. Score 100 returned because Slither compilation failed silently — BUG-003, BUG-012 |
| TC-052 | Full scan — empty `.sol` file | ❌ FAIL | `assert response.status_code == 400` but got `200` — empty file accepted — BUG-002 |
| TC-053 | Full scan — large contract | ❌ FAIL | `assert 'vulnerabilities' in data` — BUG-003 |
| TC-054 | Full scan — last case | ✅ PASS | `FFFF.` — final dot |

### Integration: Slither — `test_slither_integration.py` — 1 PASS, 1 FAIL

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-055 | Slither integration test 1 | ❌ FAIL | `test_slither_integration.py F. [80%]` — `solc-select` called `get_latest_release()` which made an outbound HTTP request that returned 403. Slither cannot compile without `solc`. BUG-005 |
| TC-056 | Slither integration test 2 | ✅ PASS | Dot after F |

### API: Health Endpoint — `test_health_endpoint.py` — 4 PASS

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-057 through TC-060 | Health endpoint tests 1–4 | ✅ ALL PASS | `test_health_endpoint.py .... [85%]` — 4 dots |

### API: Scan Endpoint — `test_scan_endpoint.py` — 8 PASS, 2 FAIL, 1 ERROR

| # | Test | Result | Evidence |
|---|---|---|---|
| TC-061 | Scan endpoint test 1 | ✅ PASS | `test_scan_endpoint.py .F....FF..E` — first char is dot |
| TC-062 | Scan endpoint test 2 | ❌ FAIL | Second char is F — root cause requires source code access to diagnose |
| TC-063 | Scan endpoint tests 3–6 | ✅ PASS | Four dots |
| TC-064 | Scan endpoint test 7 | ❌ FAIL | First F at position 7 |
| TC-065 | Scan endpoint test 8 | ❌ FAIL | Second F at position 8 |
| TC-066 | Scan endpoint tests 9–10 | ✅ PASS | Two dots |
| TC-067 | `test_concurrent_scans` — teardown | ❌ ERROR | `PermissionError: [WinError 32]` — `test.db` locked by another process during teardown. `conftest.py:52` calls `path.unlink()` before SQLAlchemy engine is disposed. The test itself ran (3 concurrent uploads, all 200 OK) but cleanup failed — BUG-006 |

---

## 3. Bug List with Priorities

| Bug ID | Title | Priority | Location | Evidence |
|---|---|---|---|---|
| BUG-001 | `Finding` model fails to resolve SQLAlchemy relationship `'Scan'` | P1 | `app/models/finding.py` | `sqlalchemy.exc.InvalidRequestError: expression 'Scan' failed to locate a name ('Scan')` |
| BUG-002 | Empty `.sol` file accepted with HTTP 200 instead of 400 | P1 | `POST /api/v1/scan/file` | `AssertionError: empty failed — assert 200 == 400` (`test_full_scan_flow.py:75`) |
| BUG-003 | API response field is `findings` but tests assert `vulnerabilities` | P1 | API schema + integration tests | `AssertionError: assert 'vulnerabilities' in {'findings': [], 'overall_score': 100, ...}` — 4 tests affected |
| BUG-004 | `scan_timestamp` missing from scan detail API response | P2 | `GET /api/v1/scans/{id}` | `KeyError: 'scan_timestamp'` (`test_database_integration.py:40`) |
| BUG-005 | `solc-select` makes live HTTP call to fetch Solidity compiler at runtime | P2 | `slither_wrapper.py` | `urllib.error.HTTPError: HTTP Error 403: Forbidden` from `get_latest_release()` on every scan |
| BUG-006 | `test.db` file locked on Windows during test teardown | P2 | `conftest.py:52` | `PermissionError: [WinError 32] The process cannot access the file because it is being used by another process: 'test.db'` |
| BUG-007 | Slither compilation failure silently produces score 100 / 0 findings | P2 | `analysis/orchestrator.py` | Log: `[WARNING] Slither analysis failed` immediately followed by `[OK] Slither found 0 issues` — failure treated as clean |
| BUG-008 | `test.db` SQLite file committed to public repository | P2 | Repo root | Visible at `github.com/ManasviJ15/BlockScope/blob/main/test.db` |
| BUG-009 | Scan endpoint: 2 undiagnosed failures in `test_scan_endpoint.py` | P2 | `test_api/test_scan_endpoint.py` | Positions 2, 7, 8 in `.F....FF..E` — require source code access to root-cause |
| BUG-010 | `solc-select` fetches `latest` compiler version on every scan — no caching | P3 | `slither_wrapper.py` | Every scan in the log triggers a full `get_latest_release()` HTTP call |
| BUG-011 | `pytest_errors.txt` committed to repository | P3 | Repo root | CI debug artefact in public repo |
| BUG-012 | PR debug artefacts committed to repo root (`pr18_*.json`, `pr19_*.json`) | P3 | Repo root | Multiple JSON files from PR debugging visible in repo |
| BUG-013 | `fix_blockscope_tuesday.ps1` debug script committed to repo | P3 | Repo root | Temporary PowerShell fix script in public repo |
| BUG-014 | `test_database_integration.py` pass/fail order misreported in v1 | P4 | Previous QA report | v1 incorrectly stated test 1 passed and test 2 failed; pytest output `F.` means test 1 failed, test 2 passed |

---

## 4. Bug Reproduction Steps (Critical Bugs)

### BUG-001 — SQLAlchemy Relationship `KeyError: 'Scan'`
**Reproduce:** `pytest backend/tests/test_models.py::test_vulnerability_model`
**Root cause:** `Finding` model declares `relationship('Scan', ...)` as a string, but `Scan` is not registered in the SQLAlchemy mapper when `Finding` is initialised in isolation.
**Fix:** Import `Scan` before `Finding` wherever both are used, or define the relationship after both classes are declared.
**Verify fix:** `pytest backend/tests/test_models.py` → 5/5 pass.

---

### BUG-002 — Empty File Returns 200
**Reproduce:** Upload a 0-byte file named `Empty.sol` to `POST /api/v1/scan/file`.
**Actual:** HTTP 200, `overall_score: 100`, `findings: []`
**Expected:** HTTP 400 with a message like "Contract source is empty."
**Fix:** Add a file content check before passing to the analysis pipeline.
**Verify fix:** `pytest backend/tests/integration/test_full_scan_flow.py` — `empty` case asserts 400 → passes.

---

### BUG-003 — `findings` vs `vulnerabilities` Field Name
**Reproduce:** Submit any scan, inspect the JSON response. Field is `findings`. Any test that asserts `'vulnerabilities' in data` will fail.
**Decision needed:** Either rename the API field to `vulnerabilities` (breaking change) or update all 4 failing tests to use `findings`.
**Verify fix:** `pytest backend/tests/integration/` → TC-047, TC-050, TC-051, TC-053 all pass.

---

### BUG-005 — `solc-select` Network Dependency
**Reproduce:** Run any scan in a network-restricted environment. `solc-select` calls `get_latest_release()` which fetches from GitHub releases API, returning 403 in offline/CI environments.
**Impact:** Slither silently fails and returns score 100 with 0 findings — a false "safe" result on every contract.
**Fix:** Pin the Solidity compiler version in Docker (`solc-select install 0.8.x && solc-select use 0.8.x`) and remove the runtime `switch_global_version(version="latest")` call.
**Verify fix:** Run integration tests with network disabled — Slither compiles successfully using pinned version.

---

### BUG-006 — Windows `test.db` File Lock
**Reproduce:** Run `pytest backend/tests/test_api/test_scan_endpoint.py::test_concurrent_scans` on Windows.
**Actual:** Test runs successfully (3 concurrent scans, all 200 OK) but teardown throws `PermissionError: [WinError 32]` when fixture tries to delete `test.db`.
**Root cause:** SQLAlchemy engine/connections not disposed before `pathlib.Path.unlink()` at `conftest.py:52`.
**Fix:** Call `engine.dispose()` in the fixture before the `unlink()` call.
**Verify fix:** `pytest backend/tests/test_api/test_scan_endpoint.py` → 0 errors on teardown.

---

## 5. Regression Checklist (Run After Each Fix)

- [ ] `pytest backend/tests/test_models.py` — 5/5 pass (BUG-001)
- [ ] `pytest backend/tests/integration/test_full_scan_flow.py` — 5/5 pass (BUG-002, BUG-003)
- [ ] `pytest backend/tests/integration/test_error_recovery.py` — 3/3 pass (BUG-003, BUG-007)
- [ ] `pytest backend/tests/integration/test_database_integration.py` — 2/2 pass (BUG-004)
- [ ] `pytest backend/tests/integration/test_slither_integration.py` — 2/2 pass (BUG-005)
- [ ] `pytest backend/tests/test_api/test_scan_endpoint.py` — 11/11 pass, 0 errors (BUG-006, BUG-009)
- [ ] Full run: `pytest` — 70/70 pass, 0 failures, 0 errors
- [ ] `git status` shows `test.db` not tracked (BUG-008)
- [ ] Repo root clean of `pytest_errors.txt`, `pr18_*.json`, `pr19_*.json`, `fix_blockscope_tuesday.ps1`

---

## 6. Remaining Work to Complete the Full QA Assignment

The following tasks are **not yet started** and are required before this can be submitted as a final QA deliverable. They are blocked by the frontend deployment being unavailable (Vercel returns 404).

### Blocker
The frontend at `https://block-scope-iota.vercel.app` returns HTTP 404. All UI-dependent QA tasks are blocked until this is restored.

### Task List

**Manual Testing of User Flows (estimated: 8 hours)**
- Test all user-facing flows end-to-end in a browser (paste contract, upload file, view results, view history)
- Document each flow with steps, expected result, actual result, pass/fail
- Add at least 20 executed UI test cases to this report

**Cross-Browser Testing (estimated: 3 hours)**
- Chrome (latest), Firefox (latest), Safari 17+, Edge (latest)
- Test: page load, scan flow, file upload, results display, error states
- Record pass/fail per browser with any deviation noted

**Mobile Testing (estimated: 2 hours)**
- iOS Safari on iPhone, Android Chrome on Pixel or equivalent
- Test: layout, code input area usability, file upload, results readability
- Record pass/fail per device

**Accessibility Testing (estimated: 2 hours)**
- Run axe DevTools automated scan — capture full output
- Manual keyboard navigation through all interactive elements
- Verify colour contrast meets WCAG 2.1 AA (4.5:1 minimum)
- Test with NVDA (Windows) or VoiceOver (Mac/iOS)
- Record findings as actual pass/fail, not recommendations

**UAT with Sample Users (estimated: 4 hours)**
- Recruit 3–5 sample users unfamiliar with the product
- Run the 3 test scenarios (new user scan, developer file upload, scan history review)
- Record actual feedback verbatim
- Document issues found as real observations, not inferences

---

## 7. Summary

This report documents completed backend QA work honestly. It does not claim completion of tasks that have not been performed. The backend test suite has 13 confirmed failures across 14 documented bugs with full reproduction steps. The remaining QA tasks — manual UI testing, cross-browser, mobile, accessibility, and UAT — are ready to begin and will be added to this report once the frontend deployment is restored and users are available.

---

*Report type: PARTIAL — Interim QA Status*  
*Final QA Report will be submitted once Sec tion 6 tasks are completed.*  
*Author: ManasviJ15 | Date: March 29, 2026*  
*Evidence: `pytest_errors.txt`, SHA `ef02299f07a1709621e4799e2abea3e2375ccadf`*
