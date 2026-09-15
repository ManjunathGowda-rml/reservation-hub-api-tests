import pytest

from api.schemas import BOOKING_ID_LIST_SCHEMA, assert_matches_schema


@pytest.mark.crud
class TestReadBooking:
    def test_get_booking_ids_returns_a_schema_valid_list(self, api_client):
        response = api_client.get_booking_ids()

        assert response.status_code == 200
        body = response.json()
        assert_matches_schema(body, BOOKING_ID_LIST_SCHEMA)
        assert len(body) > 0

    def test_get_booking_ids_can_be_filtered_by_name(self, api_client, new_booking):
        booking_id, payload, _ = new_booking

        response = api_client.get_booking_ids(firstname=payload["firstname"], lastname=payload["lastname"])

        assert response.status_code == 200
        ids = [entry["bookingid"] for entry in response.json()]
        assert booking_id in ids

    def test_get_existing_booking_returns_its_details(self, api_client, new_booking):
        booking_id, payload, _ = new_booking

        response = api_client.get_booking(booking_id)

        assert response.status_code == 200
        assert response.json() == payload

    @pytest.mark.negative
    def test_get_nonexistent_booking_returns_404(self, api_client):
        response = api_client.get_booking(999_999_999)

        assert response.status_code == 404
