"""Input-validation tests for booking creation.

These assert what a *correct* Bookings API should do, not what this
sandbox actually does. Several of them are therefore expected to fail
(red) against the live API right now - each failing assertion message is
tagged with a BUG-xxx id that is documented, with a runnable curl repro,
in BUGS.md. That red result is the point: it is the automated safety net
that would have caught the negative-price / bad-date incident from the
brief before it reached a partner.
"""
import pytest

from data.booking_factory import build_booking


@pytest.mark.negative
class TestCreateBookingInputValidation:
    def test_negative_total_price_is_rejected(self, api_client):
        """Direct regression test for the production incident: a booking
        was silently created with a negative total price.
        """
        response = api_client.create_booking(build_booking(totalprice=-500))

        assert response.status_code == 400, (
            "BUG-001: POST /booking accepts a negative totalprice and "
            f"creates the booking anyway (got {response.status_code}, expected 400)"
        )

    def test_checkout_before_checkin_is_rejected(self, api_client):
        """Direct regression test for the production incident: a booking
        was silently created with checkout before checkin.
        """
        payload = build_booking(bookingdates={"checkin": "2026-06-10", "checkout": "2026-06-01"})

        response = api_client.create_booking(payload)

        assert response.status_code == 400, (
            "BUG-002: POST /booking accepts a checkout date before the "
            f"checkin date and creates the booking anyway (got {response.status_code}, expected 400)"
        )

    @pytest.mark.boundary
    def test_zero_total_price_is_a_valid_boundary_and_is_accepted(self, api_client):
        """Zero is a legitimate boundary (e.g. a fully comped stay) and,
        unlike a negative price, should NOT be rejected.
        """
        response = api_client.create_booking(build_booking(totalprice=0))

        assert response.status_code == 200
        assert response.json()["booking"]["totalprice"] == 0

    def test_non_numeric_total_price_is_rejected(self, api_client):
        response = api_client.create_booking(build_booking(totalprice="one hundred"))

        assert response.status_code == 400, (
            "BUG-003: POST /booking accepts a non-numeric totalprice and "
            f"silently stores it as null instead of rejecting it (got {response.status_code}, expected 400)"
        )

    def test_malformed_checkin_date_is_rejected(self, api_client):
        payload = build_booking(bookingdates={"checkin": "not-a-date", "checkout": "2026-06-05"})

        response = api_client.create_booking(payload)

        assert response.status_code == 400, (
            "BUG-004: POST /booking accepts a malformed checkin date and "
            f"silently corrupts it (e.g. '0NaN-aN-aN') instead of rejecting it (got {response.status_code}, expected 400)"
        )

    @pytest.mark.parametrize(
        "missing_field", ["firstname", "lastname", "totalprice", "depositpaid", "bookingdates"]
    )
    def test_missing_required_field_is_rejected_with_400(self, api_client, missing_field):
        payload = build_booking()
        del payload[missing_field]

        response = api_client.create_booking(payload)

        assert response.status_code == 400, (
            f"BUG-005: POST /booking with '{missing_field}' missing returns "
            f"{response.status_code} Internal Server Error instead of 400 Bad Request"
        )

    def test_empty_payload_is_rejected_with_400(self, api_client):
        response = api_client.create_booking({})

        assert response.status_code == 400, (
            "BUG-005: POST /booking with an empty payload returns "
            f"{response.status_code} Internal Server Error instead of 400 Bad Request"
        )
