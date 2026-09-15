import allure
import pytest

from api.schemas import CREATE_BOOKING_RESPONSE_SCHEMA, assert_matches_schema
from data.booking_factory import build_booking


@allure.feature("Create Booking")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.crud
class TestCreateBooking:
    def test_create_booking_returns_the_booking_that_was_sent(self, api_client):
        payload = build_booking(totalprice=250, additionalneeds="Late checkout")

        response = api_client.create_booking(payload)

        assert response.status_code == 200
        body = response.json()
        assert_matches_schema(body, CREATE_BOOKING_RESPONSE_SCHEMA)
        assert isinstance(body["bookingid"], int)
        assert body["booking"] == payload

    def test_created_booking_can_be_read_back_unchanged(self, api_client, new_booking):
        booking_id, payload, _ = new_booking

        response = api_client.get_booking(booking_id)

        assert response.status_code == 200
        assert response.json() == payload
