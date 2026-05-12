# Part C – Strategy & Recommendations

---

## 1. Why These Two Tests Were Selected for Automation

### Automated Test 1 — E2E UI: Full Bet Placement Journey
This test exercises the entire critical path in one run: match rendering → selection → stake entry → loading state → receipt verification → balance deduction → Bet Slip teardown. It locks down the spec requirement that all receipt values match pre-placement values — impractical to verify manually at scale. If this test fails, a placement regression is confirmed immediately.

### Automated Test 2 — API: Stake Boundary and Semantic Validation
The API is the last enforcement layer. UI validation can be bypassed with a single `curl`. This suite exercises every documented 422 error code plus protocol-level errors (400, 401, 405) without a browser, in under 200 ms per test. It is designed to block CI builds on any backend regression before the slower UI suite runs.

---

## 2. What Was Left as Manual Only and Why

| Scenario | Reason for manual-only |
|---|---|
| TC-003 – Insufficient Balance (UI layer) | Requires chaining bets to reach specific intermediate balances — fragile, slow, data-coupled. Core risk already covered by API test. |
| TC-005 – Bet Slip Single-Selection State | Pure client-side state; low regression risk; Bet Slip control selectors are the most brittle part of the DOM. |
| TC-006 – Filters (Odds/Date) | Data-dependent: results change with the live match catalogue. Unreliable without a seeded dataset and a reliable reset (BUG-002 unresolved). |
| BUG-003 – Payout float artefacts | Requires visual inspection per stake/odds combination; DOM text comparison is insufficient without knowing how the framework serialises floats. |

---

## 3. Top Recommendations for Scaling

### 3.1 CI/CD Integration
- Run **API tests on every PR** (< 5 s, no browser).
- Run **E2E UI tests on merge to main** and nightly.
- Gate merges on API test pass; treat happy-path E2E failure as a merge blocker.

### 3.2 Seeded Test Data Strategy
- Provision a **fresh user ID per CI run** (or fix BUG-002) so tests can run in parallel without balance interference.
- Use a static match fixture so boundary-value tests don't depend on the live catalogue.

### 3.3 Contract Testing
- Add **schemathesis** or **Pact** to auto-replay the OpenAPI 3.0.3 spec on every deployment.
- This would have caught BUG-002 at the schema level immediately.

### 3.4 Spec Clarifications Required

| Item | Issue | Action |
|---|---|---|
| Minimum stake | §3 = EUR 1.00, §4.1 = EUR 1.01 | Align all sections; update tests and UI copy |
| Reset-balance consistency | API spec allows divergence; feature spec forbids it | Fix the API or remove the caveat; add automated assertion |
| Selection enum case | Lowercase silently rejected | Document explicitly; consider API-level case normalisation |
