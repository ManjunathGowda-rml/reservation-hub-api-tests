import pytest

from api.schemas import BOOKING_SCHEMA, assert_matches_schema
from data.booking_factory import build_booking


@pytest.mark.crud
class TestUpdateBooking:
    def test_put_replaces_the_whole_booking(self, api_client, new_booking, auth_headers):
        booking_id, _, _ = new_booking
        new_payload = build_booking(totalprice=777, depositpaid=False, additionalneeds="Airport transfer")

        response = api_client.update_booking(booking_id, new_payload, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert_matches_schema(body, BOOKING_SCHEMA)
        assert body == new_payload

        follow_up = api_client.get_booking(booking_id)
        assert follow_up.json() == new_payload

    def test_patch_updates_only_the_given_fields(self, api_client, new_booking, auth_headers):
        booking_id, original_payload, _ = new_booking

        response = api_client.partial_update_booking(booking_id, {"totalprice": 555}, headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["totalprice"] == 555
        for key, value in original_payload.items():
            if key != "totalprice":
                assert body[key] == value, f"PATCH unexpectedly changed untouched field '{key}'"

    @pytest.mark.negative
    def test_put_on_a_nonexistent_booking_returns_404(self, api_client, auth_headers):
        response = api_client.update_booking(999_999_999, build_booking(), headers=auth_headers)

        assert response.status_code == 404, (
            "BUG-007: PUT on a non-existent booking id returns 405 Method Not "
            f"Allowed instead of 404 Not Found (got {response.status_code})"
        )
