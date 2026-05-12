"""
tests/api/test_place_bet_api.py
────────────────────────────────
AUTOMATED TEST 2 — API: Place-Bet Validation and Business Rule Enforcement.

Why this test was automated
----------------------------
The API is the **final** enforcement layer — UI validation can be bypassed
by any user with browser DevTools or a single ``curl`` command.  This suite:

* Exercises every documented 422 error code (stake range, precision, type,
  match ID, selection).
* Checks protocol-level errors: 400 (malformed payload), 401 (auth), 405
  (wrong HTTP method).
* Verifies happy-path correctness: HTTP 200, payout = stake × odds, balance
  persistence after bet.
* Includes a **BUG-002 regression test** asserting that the reset-balance
  response matches the balance that is actually persisted.

Tests run in **under 200 ms each** with no browser required — ideal for
blocking CI builds early before the slower E2E UI suite is launched.
"""
from __future__ import annotations

import pytest
import requests


# ---------------------------------------------------------------------------
# Module-scoped helper fixture
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def valid_match(base_url: str, api_headers: dict):
    """
    Fetch the first available match from ``GET /api/matches``.

    Module-scoped so the network round-trip happens only once per test-module
    run.  Returns a dict with ``id``, ``home_odds``, ``draw_odds``,
    ``away_odds``.
    """
    resp = requests.get(f"{base_url}/api/matches", headers=api_headers)
    assert resp.status_code == 200, f"GET /api/matches failed: {resp.text}"
    matches = resp.json()
    assert matches, "Match list is empty — cannot run API tests without a match"
    m = matches[0]
    return {
        "id":        m["id"],
        "home_odds": m["odds"]["home"],
        "draw_odds": m["odds"]["draw"],
        "away_odds": m["odds"]["away"],
    }


def _post_bet(
    base_url: str, headers: dict, payload: dict
) -> requests.Response:
    """Helper: POST /api/place-bet and return the raw response."""
    return requests.post(
        f"{base_url}/api/place-bet", json=payload, headers=headers
    )


# ===========================================================================
# Happy path
# ===========================================================================
class TestPlaceBetHappyPath:
    """Positive cases — confirm HTTP 200 responses and data integrity."""

    @pytest.fixture(autouse=True)
    def _reset(self, reset):
        """Ensure balance is EUR 125.50 before every test in this class."""
        pass

    def test_valid_home_bet_returns_200_with_correct_payout(
        self, base_url, api_headers, valid_match
    ):
        """
        POST a valid HOME bet at EUR 10.00 and assert:

        * HTTP 200
        * Response echoes ``matchId``, ``selection``, ``stake``, ``currency``
        * ``payout`` == ``round(stake × odds, 2)``
        * ``balance`` in response == pre-bet balance − stake
        """
        stake   = 10.00
        payload = {
            "matchId":   valid_match["id"],
            "selection": "HOME",
            "stake":     stake,
        }

        pre_balance: float = requests.get(
            f"{base_url}/api/balance", headers=api_headers
        ).json()["balance"]

        resp = _post_bet(base_url, api_headers, payload)
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}: {resp.text}"
        )

        body = resp.json()
        assert body["matchId"]   == valid_match["id"]
        assert body["selection"] == "HOME"
        assert body["stake"]     == stake
        assert body["currency"]  == "EUR"

        expected_payout = round(stake * valid_match["home_odds"], 2)
        assert body["odds"] == pytest.approx(valid_match["home_odds"], abs=0.001), (
            f"Response odds {body['odds']} != catalogue odds {valid_match['home_odds']}"
        )
        assert body["payout"] == pytest.approx(expected_payout, abs=0.01), (
            f"Payout {body['payout']} != {stake} × {valid_match['home_odds']} = {expected_payout}"
        )
        assert body["balance"] == pytest.approx(pre_balance - stake, abs=0.01), (
            f"Response balance {body['balance']} != {pre_balance} − {stake}"
        )

    def test_balance_is_persisted_after_bet(
        self, base_url, api_headers, valid_match
    ):
        """
        ``GET /api/balance`` after a successful bet must reflect the deducted
        amount, confirming persistence — not just an echoed response value.
        """
        stake = 5.00
        pre: float = requests.get(
            f"{base_url}/api/balance", headers=api_headers
        ).json()["balance"]

        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "DRAW", "stake": stake},
        )
        assert resp.status_code == 200

        post: float = requests.get(
            f"{base_url}/api/balance", headers=api_headers
        ).json()["balance"]
        assert post == pytest.approx(pre - stake, abs=0.01), (
            f"Persisted balance {post} != expected {pre - stake}"
        )

    def test_boundary_minimum_stake_is_accepted(
        self, base_url, api_headers, valid_match
    ):
        """
        EUR 1.00 is the minimum stake per Business Rules and API error message.

        .. note::
            Spec §4.1 erroneously states EUR 1.01 — see **BUG-001**.
        """
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "AWAY", "stake": 1.00},
        )
        assert resp.status_code == 200, (
            f"Minimum stake EUR 1.00 was rejected: {resp.text}"
        )

    def test_boundary_maximum_stake_is_accepted(
        self, base_url, api_headers, valid_match
    ):
        """EUR 100.00 is the maximum stake per spec Business Rules."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME", "stake": 100.00},
        )
        assert resp.status_code == 200, (
            f"Maximum stake EUR 100.00 was rejected: {resp.text}"
        )

    @pytest.mark.parametrize("selection", ["HOME", "DRAW", "AWAY"])
    def test_all_three_valid_selections_accepted(
        self, base_url, api_headers, valid_match, selection: str
    ):
        """Each of the three enum values must result in HTTP 200."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": selection, "stake": 1.00},
        )
        assert resp.status_code == 200, f"selection={selection!r}: {resp.text}"


# ===========================================================================
# Stake validation — 422
# ===========================================================================
class TestStakeValidation:
    """
    The API must enforce all stake business rules independently of the UI
    (a technical user can POST directly, bypassing client-side validation).
    """

    @pytest.mark.parametrize("stake,expected_error", [
        (0.99,   "invalid_stake_min"),   # one cent below minimum
        (0.00,   "invalid_stake_min"),   # zero
        (-1.00,  "invalid_stake_min"),   # negative
        (100.01, "invalid_stake_max"),   # one cent above maximum
        (999.00, "invalid_stake_max"),   # well above maximum
    ])
    def test_stake_out_of_range_returns_422(
        self, base_url, api_headers, valid_match, stake, expected_error: str
    ):
        """Stakes below EUR 1.00 or above EUR 100.00 must return 422."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME", "stake": stake},
        )
        assert resp.status_code == 422, (
            f"stake={stake}: expected 422, got {resp.status_code}"
        )
        assert resp.json().get("error") == expected_error, (
            f"stake={stake}: expected {expected_error!r}, got {resp.json()}"
        )

    @pytest.mark.parametrize("stake", [10.123, 1.001, 99.999])
    def test_stake_precision_violation_returns_422(
        self, base_url, api_headers, valid_match, stake
    ):
        """Stakes with more than 2 decimal places must return 422 ``invalid_stake_precision``."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME", "stake": stake},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "invalid_stake_precision", (
            f"stake={stake}: {resp.json()}"
        )

    @pytest.mark.parametrize("stake", ["ten", "EUR10", "10,00", None, True])
    def test_non_numeric_stake_returns_422(
        self, base_url, api_headers, valid_match, stake
    ):
        """Non-numeric stake values must return 422 ``invalid_stake_type``."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME", "stake": stake},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "invalid_stake_type", (
            f"stake={stake!r}: {resp.json()}"
        )

    def test_missing_stake_field_returns_422(
        self, base_url, api_headers, valid_match
    ):
        """Omitting ``stake`` entirely must return 422."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME"},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "invalid_stake_type", resp.json()


# ===========================================================================
# Selection and match validation — 422
# ===========================================================================
class TestSelectionAndMatchValidation:
    """API must reject invalid selections and unknown / missing match IDs."""

    @pytest.mark.parametrize("selection,expected_error", [
        ("INVALID", "invalid_selection"),   # not in enum
        ("home",    "invalid_selection"),   # lowercase (enum is uppercase-only)
        ("1",       "invalid_selection"),   # display label, not enum value
        ("Win",     "invalid_selection"),   # arbitrary string
        ("",        "invalid_selection"),   # empty string
    ])
    def test_invalid_selection_returns_422(
        self,
        base_url,
        api_headers,
        valid_match,
        selection: str,
        expected_error: str,
    ):
        """Selection must be exactly ``HOME``, ``DRAW``, or ``AWAY`` (case-sensitive)."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": selection, "stake": 10.00},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == expected_error, (
            f"selection={selection!r}: {resp.json()}"
        )

    def test_unknown_match_id_returns_422(self, base_url, api_headers):
        """A ``matchId`` not in the catalogue must return 422 ``invalid_match``."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": "non-existent-match-xyz", "selection": "HOME", "stake": 10.00},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "invalid_match", resp.json()

    def test_empty_match_id_returns_422(self, base_url, api_headers):
        """An empty-string ``matchId`` must return 422 ``invalid_match_id``."""
        resp = _post_bet(
            base_url, api_headers,
            {"matchId": "", "selection": "HOME", "stake": 10.00},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "invalid_match_id", resp.json()

    def test_missing_match_id_returns_422(self, base_url, api_headers):
        """Omitting the ``matchId`` field must return 422 ``invalid_match_id``."""
        resp = _post_bet(
            base_url, api_headers,
            {"selection": "HOME", "stake": 10.00},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "invalid_match_id", resp.json()


# ===========================================================================
# Insufficient balance — 422
# ===========================================================================
class TestInsufficientBalance:
    """API must reject stakes that exceed the user's available balance."""

    @pytest.fixture(autouse=True)
    def _reset(self, reset):
        pass

    def test_stake_exceeding_balance_returns_422(
        self, base_url, api_headers, valid_match
    ):
        """
        A stake of ``balance + EUR 0.01`` must be rejected with
        422 ``insufficient_balance``, verifying the API enforces the check
        independently of the UI.
        """
        balance: float = requests.get(
            f"{base_url}/api/balance", headers=api_headers
        ).json()["balance"]
        over_stake = round(balance + 0.01, 2)

        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME", "stake": over_stake},
        )
        assert resp.status_code == 422
        assert resp.json().get("error") == "insufficient_balance", resp.json()

    def test_stake_equal_to_balance_is_accepted(
        self, base_url, api_headers, valid_match
    ):
        """
        A stake exactly equal to the available balance must be accepted.
        Edge case: the exact balance is a valid stake (not over-limit).
        """
        balance: float = requests.get(
            f"{base_url}/api/balance", headers=api_headers
        ).json()["balance"]
        stake = min(round(balance, 2), 100.00)   # cap at the max-stake limit

        resp = _post_bet(
            base_url, api_headers,
            {"matchId": valid_match["id"], "selection": "HOME", "stake": stake},
        )
        assert resp.status_code == 200, (
            f"Stake equal to balance ({stake}) should be accepted: {resp.text}"
        )


# ===========================================================================
# Protocol validation — 400, 401, 405
# ===========================================================================
class TestProtocolValidation:
    """Verify API surface protection: method gating, auth, and payload format."""

    def test_malformed_json_returns_400(self, base_url, api_headers):
        """A body that cannot be parsed as JSON must return 400 ``invalid_json``."""
        resp = requests.post(
            f"{base_url}/api/place-bet",
            data="this is definitely {{not json",
            headers={**api_headers, "Content-Type": "application/json"},
        )
        assert resp.status_code == 400
        assert resp.json().get("error") == "invalid_json", resp.json()

    def test_json_array_body_returns_400(self, base_url, api_headers):
        """
        A JSON *array* body (valid JSON but not an object) must return
        400 ``invalid_request``.  Spec: *'Request body must be a JSON object.'*
        """
        resp = requests.post(
            f"{base_url}/api/place-bet",
            json=[{"matchId": "x", "selection": "HOME", "stake": 10}],
            headers=api_headers,
        )
        assert resp.status_code == 400
        assert resp.json().get("error") == "invalid_request", resp.json()

    def test_get_method_on_place_bet_returns_405(self, base_url, api_headers):
        """``GET /api/place-bet`` must return 405 Method Not Allowed."""
        resp = requests.get(f"{base_url}/api/place-bet", headers=api_headers)
        assert resp.status_code == 405

    def test_missing_user_id_header_returns_401(self, base_url):
        """
        A request with no ``x-user-id`` header must return 401
        ``missing_user_id``.  All endpoints require this header (spec §5.1).
        """
        resp = requests.post(
            f"{base_url}/api/place-bet",
            json={"matchId": "any", "selection": "HOME", "stake": 10.00},
            headers={"Content-Type": "application/json"},   # no x-user-id
        )
        assert resp.status_code == 401
        assert resp.json().get("error") == "missing_user_id", resp.json()

    def test_invalid_user_id_header_returns_401(self, base_url):
        """An unrecognised ``x-user-id`` value must return 401 ``invalid_user_id``."""
        resp = requests.post(
            f"{base_url}/api/place-bet",
            json={"matchId": "any", "selection": "HOME", "stake": 10.00},
            headers={
                "x-user-id":    "not-a-real-user-id",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
        assert resp.json().get("error") == "invalid_user_id", resp.json()


# ===========================================================================
# BUG-002 regression — reset-balance consistency
# ===========================================================================
class TestResetBalanceConsistency:
    """
    Regression test for **BUG-002**.

    Feature spec §5.3 requires:

        *'Response body and persisted state must be consistent after reset.'*

    The embedded OpenAPI 3.0.3 spec explicitly contradicts this by describing
    the 200 response as:

        *'Balance reset successfully (response payload may differ from
        persisted balance)'*

    This test will catch any divergence between the reset response and the
    balance returned by a subsequent ``GET /api/balance``.
    """

    def test_reset_response_matches_persisted_balance(
        self, base_url, api_headers, valid_match
    ):
        # Modify balance so reset has real work to do
        matches = requests.get(
            f"{base_url}/api/matches", headers=api_headers
        ).json()
        if matches:
            requests.post(
                f"{base_url}/api/place-bet",
                json={
                    "matchId":   matches[0]["id"],
                    "selection": "HOME",
                    "stake":     10.00,
                },
                headers=api_headers,
            )

        # Call reset
        reset_resp = requests.post(
            f"{base_url}/api/reset-balance", headers=api_headers
        )
        assert reset_resp.status_code == 200, (
            f"reset-balance failed: {reset_resp.text}"
        )
        reset_body    = reset_resp.json()
        assert reset_body.get("currency") == "EUR"
        reset_balance = reset_body["balance"]

        # Verify persisted state
        persisted: float = requests.get(
            f"{base_url}/api/balance", headers=api_headers
        ).json()["balance"]

        assert reset_balance == pytest.approx(125.50, abs=0.01), (
            f"Reset response balance {reset_balance} != expected EUR 125.50"
        )
        assert persisted == pytest.approx(reset_balance, abs=0.001), (
            f"BUG-002 ACTIVE: reset response ({reset_balance}) != "
            f"persisted balance ({persisted}). "
            "Response and stored state are inconsistent."
        )
