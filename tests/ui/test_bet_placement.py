"""
tests/ui/test_bet_placement.py
──────────────────────────────
AUTOMATED TEST 1 — End-to-End UI: Successful Single Bet Placement and Receipt Integrity.

Why this test was automated
----------------------------
This test covers the entire primary revenue transaction end-to-end:

    match rendering  →  odds selection  →  stake entry  →  loading state
    →  receipt verification  →  balance deduction  →  Bet Slip teardown

A single automated run validates six system boundaries simultaneously.
It also enforces the spec requirement that **all receipt values must match
the values the user saw before placing** — an invariant that is impractical
to verify manually at scale but trivially expressed as pytest assertions.

If this test fails, a bet placement regression is confirmed with zero ambiguity.
"""
from __future__ import annotations

import re

import pytest

from pages.betting_page import BettingPage


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _to_float(text: str) -> float:
    """Strip currency symbols / whitespace and parse to ``float``.

    Examples
    --------
    ``'EUR 24.50'``  →  ``24.5``
    ``'€115.50'``    →  ``115.5``
    """
    return float(re.sub(r"[^\d.]", "", text))


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------
class TestBetPlacementHappyPath:
    """End-to-end tests for the single bet placement user journey."""

    @pytest.fixture(autouse=True)
    def _setup(self, driver):
        """Inject driver and wait for matches to load before every test in the class."""
        self.page = BettingPage(driver)
        self.page.wait_for_matches()

    # ── Core happy path ───────────────────────────────────────────────────
    def test_full_bet_receipt_data_integrity(self):
        """
        TC-001 full happy path.

        Steps verified
        --------------
        1. Starting balance is EUR 125.50 (after reset fixture).
        2. Bet Slip reflects the correct match name, selection, and odds.
        3. Payout preview = stake × odds before placement.
        4. Place Bet button enters *Placing...* loading state on click.
        5. Every receipt field matches the pre-placement value exactly:
           Bet ID, Match, Selection, Stake, Odds, Payout, Timestamp.
        6. Header balance decreases by exactly the stake amount after close.
        7. Bet Slip is fully cleared after the receipt modal is closed.
        """
        STAKE = 10.00

        # 1 ── Pre-placement state ──────────────────────────────────────────
        pre_balance = _to_float(self.page.get_header_balance())
        assert pre_balance == pytest.approx(125.50, abs=0.01), (
            f"Expected starting balance EUR 125.50, got {pre_balance}"
        )

        match_label = self.page.get_match_label(card_index=0)
        odds_text   = self.page.click_home_odds(card_index=0)
        odds_value  = float(odds_text)

        # 2 ── Bet Slip content ─────────────────────────────────────────────
        slip = self.page.get_betslip_snapshot()
        assert slip.match == match_label, (
            f"Bet Slip match {slip.match!r} != card match {match_label!r}"
        )
        assert "HOME" in slip.selection.upper(), (
            f"Expected HOME selection, got {slip.selection!r}"
        )
        assert float(slip.odds) == pytest.approx(odds_value, abs=0.001), (
            f"Bet Slip odds {slip.odds} != card odds {odds_value}"
        )

        # 3 ── Stake and payout preview ─────────────────────────────────────
        self.page.enter_stake(str(STAKE))
        expected_payout = round(STAKE * odds_value, 2)
        slip2 = self.page.get_betslip_snapshot()
        assert _to_float(slip2.payout) == pytest.approx(expected_payout, abs=0.01), (
            f"Bet Slip payout {slip2.payout} != {STAKE} × {odds_value} = {expected_payout}"
        )

        # 4 ── Placement (loading state asserted inside click_place_bet) ────
        self.page.click_place_bet()

        # 5 ── Receipt field verification ───────────────────────────────────
        receipt = self.page.get_receipt()

        assert receipt.bet_id, "Receipt Bet ID must not be empty"
        assert receipt.match == match_label, (
            f"Receipt match {receipt.match!r} != pre-placement {match_label!r}"
        )
        assert "HOME" in receipt.selection.upper(), (
            f"Receipt selection {receipt.selection!r} should indicate HOME"
        )
        assert _to_float(receipt.stake) == pytest.approx(STAKE, abs=0.001), (
            f"Receipt stake {receipt.stake} != placed stake EUR {STAKE}"
        )
        assert float(receipt.odds) == pytest.approx(odds_value, abs=0.001), (
            f"Receipt odds {receipt.odds} != pre-placement odds {odds_value}"
        )
        assert _to_float(receipt.payout) == pytest.approx(expected_payout, abs=0.01), (
            f"Receipt payout {receipt.payout} != expected EUR {expected_payout}"
        )
        assert receipt.timestamp, "Receipt timestamp must not be empty"

        # 6 & 7 ── Post-close state ─────────────────────────────────────────
        self.page.close_receipt()

        post_balance = _to_float(self.page.get_header_balance())
        assert post_balance == pytest.approx(pre_balance - STAKE, abs=0.01), (
            f"Balance after bet: expected EUR {pre_balance - STAKE:.2f}, got {post_balance}"
        )
        assert self.page.is_betslip_empty(), (
            "Bet Slip must be empty after the receipt modal is closed"
        )

    # ── Loading state ─────────────────────────────────────────────────────
    def test_place_bet_shows_placing_loading_state(self):
        """
        Spec §2.3: the Place Bet button must enter a *Placing...* state between
        click and receipt.  Prevents double-click race conditions that could
        submit duplicate bets.  ``click_place_bet()`` raises
        ``TimeoutException`` if the indicator never appears.
        """
        self.page.click_home_odds(card_index=0)
        self.page.enter_stake("5.00")
        self.page.click_place_bet()
        self.page.wait_for_receipt()   # confirms the flow resolves to success

    # ── Stake validation — UI layer ───────────────────────────────────────
    @pytest.mark.parametrize("stake,expected_fragment", [
        ("0.99",   "1.00"),     # below minimum
        ("100.01", "100"),      # above maximum
        ("10.123", "decimal"),  # precision violation
    ])
    def test_invalid_stake_shows_ui_error(self, stake: str, expected_fragment: str):
        """
        The UI must display a validation message for stakes outside the allowed
        boundaries.  Covers below-minimum, above-maximum, and precision cases.
        """
        self.page.click_home_odds(card_index=0)
        self.page.enter_stake(stake)
        error = self.page.get_stake_error()
        assert error, (
            f"Expected a stake validation error for {stake!r} — none was shown"
        )
        assert expected_fragment.lower() in error.lower(), (
            f"Error message {error!r} does not mention expected text {expected_fragment!r}"
        )

    def test_minimum_stake_is_accepted_by_ui(self):
        """
        Boundary EUR 1.00 must be accepted (spec Business Rules and UI copy both
        state EUR 1.00).

        .. note::
            Spec §4.1 Validation Rules contradictorily states EUR 1.01.
            See **BUG-001** in docs/bug_report.md.
        """
        self.page.click_home_odds(card_index=0)
        self.page.enter_stake("1.00")
        assert self.page.is_place_bet_enabled(), (
            "Place Bet should be enabled for the minimum valid stake EUR 1.00"
        )
        assert not self.page.get_stake_error(), (
            "No validation error should appear for stake EUR 1.00"
        )

    def test_maximum_stake_is_accepted_by_ui(self):
        """Boundary EUR 100.00 must be accepted (spec Business Rules)."""
        self.page.click_home_odds(card_index=0)
        self.page.enter_stake("100.00")
        assert self.page.is_place_bet_enabled(), (
            "Place Bet should be enabled for the maximum valid stake EUR 100.00"
        )

    def test_insufficient_balance_blocked_by_ui(self):
        """
        A stake above the current balance must be blocked by the UI with a
        message containing *insufficient* or *balance* (spec §4.4).
        """
        self.page.click_home_odds(card_index=0)
        self.page.enter_stake("125.51")   # EUR 0.01 above the EUR 125.50 starting balance
        error = self.page.get_stake_error()
        assert error, "Expected an error message for stake exceeding the balance"
        assert "insufficient" in error.lower() or "balance" in error.lower(), (
            f"Error {error!r} should mention insufficient balance"
        )
