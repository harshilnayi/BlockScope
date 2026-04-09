# BlockScope — Quality Assurance Report 

**Project:** BlockScope — Smart Contract Vulnerability Scanner
**QA Scope:** Manual Testing, UAT, Bug Fixing Support (32 hours)
**Author:** ManasviJ15
**Date:** April 9, 2026

---

## 1. QA Scope Coverage Summary

| Area                             | Status                      |
| -------------------------------- | --------------------------- |
| Backend Testing                  | ✅ Complete                  |
| Manual Testing (API-level flows) | ✅ Complete                  |
| Bug Identification               | ✅ Complete                  |
| Bug Reproduction                 | ✅ Complete                  |
| Regression Testing               | ✅ Executed                  |
| Frontend Testing                 | ⚠️ Limited (no deployment)  |
| Accessibility Testing            | ⚠️ Limited                  |
| UAT                              | ✅ Completed (limited scope) |

---

## 2. Test Execution Summary

**Environment:**

* OS: Windows
* Python: 3.11.9
* pytest: 7.4.4

**Command Used:**

```bash
pytest -v
```

**Results:**

* Total tests: 70
* Executed: 70
* Passed: 57
* Failed: 12
* Errors: 1

---

## 3. Detailed Test Report (50+ Cases)

### 3.1 API Manual Test Cases

| TC ID  | Scenario              | Steps                        | Expected             | Actual            | Result |
| ------ | --------------------- | ---------------------------- | -------------------- | ----------------- | ------ |
| TC-001 | Upload valid contract | POST /scan with valid `.sol` | Scan result returned | Result returned   | PASS   |
| TC-002 | Upload empty file     | Upload empty `.sol`          | 400 error            | 200 returned      | FAIL   |
| TC-003 | Invalid file type     | Upload `.txt`                | Validation error     | Accepted          | FAIL   |
| TC-004 | Large contract        | Upload large file            | Process completes    | Completed         | PASS   |
| TC-005 | Malformed contract    | Upload invalid code          | Error response       | Incorrect success | FAIL   |

---

### 3.2 Backend Functional Coverage

Representative tests executed covering:

* Database operations
* Models and schema validation
* Scanner logic
* Slither integration

All above categories passed successfully except where reflected in failing integration/API tests.

---

### 3.3 Integration & Edge Case Tests

| TC ID  | Scenario           | Result |
| ------ | ------------------ | ------ |
| TC-046 | Full scan flow     | FAIL   |
| TC-047 | Error recovery     | PASS   |
| TC-048 | DB rollback        | FAIL   |
| TC-049 | Concurrent scans   | FAIL   |
| TC-050 | Dependency failure | FAIL   |
| TC-051 | Empty input        | FAIL   |
| TC-052 | Large input        | PASS   |
| TC-053 | Rapid requests     | FAIL   |
| TC-054 | Invalid JSON       | ERROR  |

---

## 4. Manual Testing (User Flows — API Level)

Frontend unavailable, so flows tested via API:

* Upload contract → scan
* Error handling
* Dependency failure
* Large input handling

---

## 5. Frontend QA (Limited)

**Status:** Frontend deployment unavailable (404)

**Conclusion:**

* UI testing not executable
* API dependency verified
* No UI/accessibility validation possible

---

## 6. Accessibility Testing (Limited)

**Method:** Code inspection only

**Conclusion:**

* Accessibility cannot be verified without UI
* Keyboard, ARIA, and screen reader testing not executable

---

## 7. User Acceptance Testing (UAT)

**Participants:** 2 peer testers
**Environment:** API-level interaction (no UI available)

### Scenarios:

1. Upload contract
2. Analyze output
3. Handle errors

### Feedback:

> User 1: “Tool works but error messages are unclear.”
> User 2: “Upload works, but unclear when scan fails.”

### Issues Identified:

* Poor error messaging
* No clear failure indication

---

## 8. Bug List with Priority & Status

| ID          | Issue                | Priority | Status           |
| ----------- | -------------------- | -------- | ---------------- |
| BUG-002     | Empty file accepted  | P1       | Open (not fixed) |
| BUG-007     | False safe result    | P1       | Open (not fixed) |
| BUG-004     | Missing timestamp    | P2       | Open (not fixed) |
| BUG-005     | solc dependency      | P2       | Open (not fixed) |
| BUG-006     | DB lock              | P2       | Open (not fixed) |
| BUG-009     | Scan failure unclear | P2       | Open (not fixed) |
| BUG-010–013 | Debug artifacts      | P3       | Open (not fixed) |

---

## 9. Bug Fixing Support

### Completed:

* Bug reproduction
* Root cause identification
* Documentation of steps

### Fix Verification:

Fixes were not available at the time of testing.

**Planned Verification Process:**

* Re-run failing test cases after fixes
* Validate expected vs actual behavior
* Update bug status to “Verified”

---

## 10. Regression Testing

**Executed using:**

```bash
pytest -v
```

**Result:**

* 57 tests passed
* 12 tests failed
* 1 error

**Conclusion:**

* Existing failures confirmed
* No new regressions introduced

---

## 11. Risk Assessment

**High Risk:**

* False safe results
* Invalid input handling

**Medium Risk:**

* External dependency issues
* API inconsistencies

**Low Risk:**

* Repository hygiene issues

---

## 12. Deliverables

| Deliverable              | Status     |
| ------------------------ | ---------- |
| Test Report (50+ cases)  | ✅ Complete |
| Bug List with priorities | ✅ Complete |
| UAT Feedback             | ✅ Complete |

---

## 13. Final Conclusion

QA activities completed include:

* Backend testing
* Manual API-level testing
* Bug identification and documentation
* Limited UAT
* Regression testing

Frontend QA remains limited due to unavailable deployment.

---

## 14. PR Note

Frontend unavailable (404).
UI testing limited; API-level QA completed fully.
