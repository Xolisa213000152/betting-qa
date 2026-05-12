"""
pages/betting_page.py – Page Object for the Sports Betting QA application.

All DOM locators live here.  Tests call descriptive methods rather than
querying the DOM directly, which keeps test code readable and makes
selector updates a single-file change.

Selector strategy
-----------------
``data-testid`` attributes are the primary strategy (most stable across
UI refactors).  If the rendered HTML does not include ``data-testid`` on
a particular element, fall back to ``aria-label`` or role + text XPath.

.. note::
    This is a React / Next.js SPA.  Confirm actual ``data-testid`` values
    against the live app with browser DevTools before running the UI tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from pages.base_page import BasePage


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass
class ReceiptData:
    """Typed snapshot of every field shown on the success receipt modal."""

    bet_id: str
    match: str
    selection: str
    stake: str
    odds: str
    payout: str
    timestamp: str


@dataclass
class BetSlipSnapshot:
    """Typed snapshot of the Bet Slip panel captured before placement."""

    match: str
    selection: str
    odds: str
    payout: str


# ---------------------------------------------------------------------------
# Page Object
# ---------------------------------------------------------------------------
class BettingPage(BasePage):
    """
    Interaction layer for:

    * Match list  (cards, odds buttons)
    * Header balance
    * Bet Slip    (stake input, payout preview, place / remove controls)
    * Success receipt modal
    * Error modal
    """

    # ── Match list ────────────────────────────────────────────────────────
    MATCH_CARDS  = (By.CSS_SELECTOR, "[data-testid='match-card']")
    MATCH_LABEL  = (By.CSS_SELECTOR, "[data-testid='match-label']")
    ODDS_HOME    = (By.CSS_SELECTOR, "[data-testid='odds-home']")
    ODDS_DRAW    = (By.CSS_SELECTOR, "[data-testid='odds-draw']")
    ODDS_AWAY    = (By.CSS_SELECTOR, "[data-testid='odds-away']")

    # ── Header ────────────────────────────────────────────────────────────
    HEADER_BALANCE = (By.CSS_SELECTOR, "[data-testid='header-balance']")

    # ── Bet Slip ──────────────────────────────────────────────────────────
    BETSLIP_MATCH       = (By.CSS_SELECTOR, "[data-testid='betslip-match']")
    BETSLIP_SELECTION   = (By.CSS_SELECTOR, "[data-testid='betslip-selection']")
    BETSLIP_ODDS        = (By.CSS_SELECTOR, "[data-testid='betslip-odds']")
    BETSLIP_PAYOUT      = (By.CSS_SELECTOR, "[data-testid='betslip-payout']")
    BETSLIP_STAKE_INPUT = (By.CSS_SELECTOR, "[data-testid='stake-input']")
    BETSLIP_STAKE_ERROR = (By.CSS_SELECTOR, "[data-testid='stake-error']")
    PLACE_BET_BUTTON    = (By.CSS_SELECTOR, "[data-testid='place-bet-button']")
    REMOVE_ALL_BUTTON   = (By.CSS_SELECTOR, "[data-testid='remove-all-button']")
    REMOVE_SELECTION    = (By.CSS_SELECTOR, "[data-testid='remove-selection']")
    PLACING_INDICATOR   = (By.XPATH,        "//*[contains(text(), 'Placing')]")

    # ── Success receipt modal ─────────────────────────────────────────────
    RECEIPT_MODAL     = (By.CSS_SELECTOR, "[data-testid='receipt-modal']")
    RECEIPT_BET_ID    = (By.CSS_SELECTOR, "[data-testid='receipt-bet-id']")
    RECEIPT_MATCH     = (By.CSS_SELECTOR, "[data-testid='receipt-match']")
    RECEIPT_SELECTION = (By.CSS_SELECTOR, "[data-testid='receipt-selection']")
    RECEIPT_STAKE     = (By.CSS_SELECTOR, "[data-testid='receipt-stake']")
    RECEIPT_ODDS      = (By.CSS_SELECTOR, "[data-testid='receipt-odds']")
    RECEIPT_PAYOUT    = (By.CSS_SELECTOR, "[data-testid='receipt-payout']")
    RECEIPT_TIMESTAMP = (By.CSS_SELECTOR, "[data-testid='receipt-timestamp']")
    RECEIPT_CLOSE     = (By.CSS_SELECTOR, "[data-testid='receipt-close']")

    # ── Error modal ───────────────────────────────────────────────────────
    ERROR_MODAL       = (By.CSS_SELECTOR, "[data-testid='error-modal']")
    ERROR_MODAL_TITLE = (By.CSS_SELECTOR, "[data-testid='error-modal-title']")
    ERROR_REBET       = (By.CSS_SELECTOR, "[data-testid='error-rebet-button']")
    ERROR_CLOSE       = (By.CSS_SELECTOR, "[data-testid='error-close-button']")

    # ── Match list helpers ────────────────────────────────────────────────
    def wait_for_matches(self) -> None:
        """Block until at least one match card is visible on the page."""
        self.wait_for(self.MATCH_CARDS)

    def get_match_count(self) -> int:
        return len(self.driver.find_elements(*self.MATCH_CARDS))

    def _card(self, index: int):
        cards = self.driver.find_elements(*self.MATCH_CARDS)
        if index >= len(cards):
            raise IndexError(
                f"Card index {index} requested but only {len(cards)} card(s) found."
            )
        return cards[index]

    def get_match_label(self, card_index: int = 0) -> str:
        """Return the match label text, e.g. ``'Manchester Utd vs Chelsea'``."""
        return self._card(card_index).find_element(*self.MATCH_LABEL).text.strip()

    def click_home_odds(self, card_index: int = 0) -> str:
        """Click the HOME (1) odds button and return the displayed odds text."""
        btn  = self._card(card_index).find_element(*self.ODDS_HOME)
        odds = btn.text.strip()
        btn.click()
        return odds

    def click_draw_odds(self, card_index: int = 0) -> str:
        """Click the DRAW (X) odds button and return the displayed odds text."""
        btn  = self._card(card_index).find_element(*self.ODDS_DRAW)
        odds = btn.text.strip()
        btn.click()
        return odds

    def click_away_odds(self, card_index: int = 0) -> str:
        """Click the AWAY (2) odds button and return the displayed odds text."""
        btn  = self._card(card_index).find_element(*self.ODDS_AWAY)
        odds = btn.text.strip()
        btn.click()
        return odds

    # ── Header helpers ────────────────────────────────────────────────────
    def get_header_balance(self) -> str:
        """Return the balance string shown in the page header, e.g. ``'EUR 125.50'``."""
        return self.text(self.HEADER_BALANCE)

    # ── Bet Slip helpers ──────────────────────────────────────────────────
    def enter_stake(self, amount: str) -> None:
        """Clear the stake input and type *amount*."""
        self.fill(self.BETSLIP_STAKE_INPUT, amount)

    def get_stake_error(self) -> str:
        """Return the stake validation error message, or ``''`` if none is shown."""
        return (
            self.text(self.BETSLIP_STAKE_ERROR)
            if self.is_present(self.BETSLIP_STAKE_ERROR)
            else ""
        )

    def get_betslip_snapshot(self) -> BetSlipSnapshot:
        """Capture the current Bet Slip state as a typed snapshot."""
        return BetSlipSnapshot(
            match     = self.text(self.BETSLIP_MATCH),
            selection = self.text(self.BETSLIP_SELECTION),
            odds      = self.text(self.BETSLIP_ODDS),
            payout    = self.text(self.BETSLIP_PAYOUT),
        )

    def is_place_bet_enabled(self) -> bool:
        """Return ``True`` if the Place Bet button is currently enabled."""
        return self.wait_for_clickable(self.PLACE_BET_BUTTON).is_enabled()

    def click_place_bet(self) -> None:
        """
        Click Place Bet and assert the loading-state indicator appears.

        Raises ``TimeoutException`` if *Placing...* never appears — which
        confirms the spec §2.3 requirement for a loading state on submit.
        """
        self.click(self.PLACE_BET_BUTTON)
        self.wait_for(self.PLACING_INDICATOR)

    def click_remove_all(self) -> None:
        """Click the *Remove All* button on the Bet Slip."""
        self.click(self.REMOVE_ALL_BUTTON)

    def click_remove_selection(self) -> None:
        """Click the per-selection *×* remove button on the Bet Slip."""
        self.click(self.REMOVE_SELECTION)

    def is_betslip_empty(self) -> bool:
        """Return ``True`` when no active selection is shown in the Bet Slip."""
        return not self.is_present(self.BETSLIP_MATCH, timeout=3)

    # ── Receipt modal helpers ─────────────────────────────────────────────
    def wait_for_receipt(self, timeout: int = 15) -> None:
        """Block until the success receipt modal is visible."""
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(self.RECEIPT_MODAL)
        )

    def get_receipt(self) -> ReceiptData:
        """Wait for the receipt modal and return all field values as a typed object."""
        self.wait_for_receipt()
        return ReceiptData(
            bet_id    = self.text(self.RECEIPT_BET_ID),
            match     = self.text(self.RECEIPT_MATCH),
            selection = self.text(self.RECEIPT_SELECTION),
            stake     = self.text(self.RECEIPT_STAKE),
            odds      = self.text(self.RECEIPT_ODDS),
            payout    = self.text(self.RECEIPT_PAYOUT),
            timestamp = self.text(self.RECEIPT_TIMESTAMP),
        )

    def close_receipt(self) -> None:
        """Click the receipt close button and wait for the modal to disappear."""
        self.click(self.RECEIPT_CLOSE)
        self.wait_invisible(self.RECEIPT_MODAL)

    # ── Error modal helpers ───────────────────────────────────────────────
    def wait_for_error_modal(self, timeout: int = 15) -> None:
        """Block until the error modal is visible."""
        WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(self.ERROR_MODAL)
        )

    def get_error_title(self) -> str:
        """Return the title text from the error modal."""
        return self.text(self.ERROR_MODAL_TITLE)

    def click_rebet(self) -> None:
        """Click the primary *Rebet* action on the error modal."""
        self.click(self.ERROR_REBET)

    def click_error_close(self) -> None:
        """Click the secondary *Close* action on the error modal."""
        self.click(self.ERROR_CLOSE)
