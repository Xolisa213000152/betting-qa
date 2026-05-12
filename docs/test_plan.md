# Single Bet Placement Feature – QA Test Plan

**Application:** Sports Betting QA App  
**Scope:** Single bet placement — pre-match, desktop web, EUR, football only  
**API Base:** https://qae-assignment-tau.vercel.app/api  
**Auth Header:** `x-user-id: candidate-K9vTb3Hd6Z`

---

## Approach

Scenarios are ordered by financial and data-integrity risk first, then UX state
management, then lower-risk discovery cases. TC-001 (happy path) is the anchor;
all other scenarios depend on the baseline flow working. Boundary and negative cases
probe each business rule at both UI and API layers independently — because UI
validation can be bypassed with a direct HTTP call.

---

## TC-001 – Happy Path: Successful Bet Placement and Receipt Integrity

**Priority:** Critical  
**Risk Rationale:** The primary revenue transaction. Incorrect receipt data, wrong balance deduction, or payout miscalculation affects every placed bet. The spec mandates receipt values match pre-placement values exactly.

### Steps
1. Open app with `?user-id=candidate-K9vTb3Hd6Z`. Header shows **EUR 125.50**.
2. Record `homeTeam`, `awayTeam`, and the HOME odds value from the first match.
3. Click the **1** (HOME) odds button. Verify Bet Slip shows correct match, selection, odds.
4. Enter stake **EUR 10.00**. Verify Payout preview = stake × odds.
5. Click **Place Bet**. Button enters **Placing...** loading state.
6. Wait for success receipt modal. Verify all fields: Bet ID, Match, Selection, Stake, Odds, Payout, Timestamp.
7. Close receipt. Verify: Bet Slip empty, balance = previous − EUR 10.00.

**Expected Result:** All receipt fields match pre-placement values. Balance deducted correctly.

---

## TC-002 – Stake Boundary and Precision Validation

**Priority:** Critical  
**Risk Rationale:** Over-max stakes breach the liability ceiling; under-min stakes create accounting noise; >2 decimal places produce unresolvable payouts. Both UI and API must enforce these limits independently.

### Steps

| # | Stake | Expected UI | Expected API |
|---|---|---|---|
| A | 0.99 | Blocked – "Minimum stake is EUR 1.00" | 422 `invalid_stake_min` |
| B | 1.00 | Accepted | 200 |
| C | 100.00 | Accepted | 200 |
| D | 100.01 | Blocked – "Maximum stake is EUR 100.00" | 422 `invalid_stake_max` |
| E | 10.123 | Blocked – precision error | 422 `invalid_stake_precision` |
| F | 0 | Blocked | 422 `invalid_stake_min` |
| G | abc | Non-numeric rejected | 422 `invalid_stake_type` |
| H | blank | Place Bet disabled | 422 `invalid_stake_type` |

> **Spec Note (BUG-001):** §3 Business Rules, §4.4 UI copy, and the API all state min = EUR 1.00.  
> §4.1 Validation Rules states EUR 1.01. This contradiction must be resolved.

---

## TC-003 – Insufficient Balance Rejection

**Priority:** Critical  
**Risk Rationale:** A bet exceeding the user's balance creates a negative balance — direct financial loss. The API must enforce this independently of the UI.

### Steps
1. Stake EUR 125.51 (balance + EUR 0.01) → UI shows "Insufficient balance", blocks submission.
2. API: POST `stake: 125.51` → HTTP 422, `error: insufficient_balance`.
3. Stake equal to remaining balance (EUR 5.00 when balance = EUR 5.00) → Accepted.
4. Balance = EUR 0.00, stake EUR 0.01 → Rejected.

---

## TC-004 – API Semantic and Protocol Validation

**Priority:** High  
**Risk Rationale:** The API is the final enforcement layer. All 422 codes must fire. Protocol errors (400, 401, 405) protect the API surface.

### Steps

| # | Request | Expected HTTP | Expected error |
|---|---|---|---|
| A | POST – `selection: "INVALID"` | 422 | `invalid_selection` |
| B | POST – `matchId: "does-not-exist"` | 422 | `invalid_match` |
| C | POST – `matchId: ""` | 422 | `invalid_match_id` |
| D | POST – matchId omitted | 422 | `invalid_match_id` |
| E | POST – body is JSON array | 400 | `invalid_request` |
| F | POST – malformed JSON | 400 | `invalid_json` |
| G | GET `/api/place-bet` | 405 | method not allowed |
| H | POST – no `x-user-id` header | 401 | `missing_user_id` |
| I | POST – `x-user-id: "bad-id"` | 401 | `invalid_user_id` |

---

## TC-005 – Bet Slip State: Single Selection and UI Controls

**Priority:** High  
**Risk Rationale:** Multiple simultaneous selections could place the wrong bet. Non-functional remove controls trap the user.

### Steps
1. Click HOME on Match A → Bet Slip shows Match A / HOME.
2. Click DRAW on Match B → Bet Slip replaces with Match B / DRAW (one active only).
3. Click × (per-selection remove) → Bet Slip clears completely.
4. Select HOME, enter stake → click **Remove All** → Bet Slip clears.
5. With empty Bet Slip, click **Remove All** → no error or crash.

---

## TC-006 – Reset Balance Consistency and Filters

**Priority:** Medium  
**Risk Rationale:** Inconsistent reset breaks test isolation. The API spec openly notes the response "may differ from persisted balance" — directly contradicting the feature spec (BUG-002).

### Steps
1. Place a bet; balance drops below EUR 125.50.
2. POST `/api/reset-balance` → note `balance` in response.
3. GET `/api/balance` → verify matches reset response (both must be EUR 125.50).
4. Reload page → verify UI header also shows EUR 125.50.
5. Apply odds filter min=3.00, max=1.00 → verify visible error feedback (invalid range).
6. Apply date filter range → verify boundary dates inclusive.

---

## Notes
- Critical defects identified: minimum stake acceptance, precision validation, reset balance inconsistency.
- High defects: error modal retry, bet slip state management.
- Medium defects: filter behavior, UI refresh after reset.
