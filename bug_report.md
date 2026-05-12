
## Test Execution Report

### Top 3 Scenarios Executed
1. **TC01 – Place Valid Single Bet**  
   - **Result**: Passed  
   - **Notes**: Receipt modal displayed correctly, balance deducted.

2. **TC02 – Reject Stake < €1.00**  
   - **Result**: Failed  
   - **Notes**: System allowed €0.50 stake, receipt generated, balance deducted incorrectly.

3. **TC05 – Reject Bet Exceeding Balance**  
   - **Result**: Passed  
   - **Notes**: Error message “Insufficient balance” displayed, bet blocked.

---

## Bug Reports

### Bug 001 – Stake Below Minimum Accepted
- **Severity**: Critical  
- **Expected**: Reject < €1.00 stake.  
- **Actual**: €0.50 accepted, receipt generated, balance deducted.  
- **Impact**: Violates business rules, financial risk.

---

### Bug 002 – Error Modal Retry Does Not Reattempt
- **Severity**: High  
- **Expected**: Retry reattempts bet placement.  
- **Actual**: Modal closes, no API request sent.  
- **Impact**: Users cannot recover from transient errors.

---

### Bug 003 – Stake Precision Validation Missing
- **Severity**: Medium  
- **Expected**: Reject >2 decimal places.  
- **Actual**: €10.123 accepted, payout calculated.  
- **Impact**: Risk of payout miscalculations.

---

## Exploratory Testing Notes
- **Filters**: Date filter fails for ranges.  
- **Odds Buttons**: Multiple selections highlighted simultaneously.  
- **Balance Reset**: API reset works, but UI header does not refresh until reload.

---

## Summary
- **Critical flows (TC01, TC05)**: Stable and aligned with plan.  
- **Validation rules (TC02, TC04)**: Failed; defects found exactly where plan anticipated risk.  
- **Error handling (TC06)**: Failed; retry logic missing.  
- **Exploratory checks**: Additional UX/state issues uncovered.  

**Conclusion:** The test plan successfully identified high‑risk defects. Critical issues (minimum stake acceptance, retry logic) must be fixed before release.
