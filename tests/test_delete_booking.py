import allure
import pytest

from data.booking_factory import build_booking


@allure.feature("Delete Booking")
@pytest.mark.crud
class TestDeleteBooking:
    @allure.severity(allure.severity_level.CRITICAL)
    def test_delete_removes_the_booking(self, api_client, admin_token):
        create_response = api_client.create_booking(build_booking())
        booking_id = create_response.json()["bookingid"]
        headers = api_client.cookie_header(admin_token)

        delete_response = api_client.delete_booking(booking_id, headers=headers)
        assert delete_response.status_code in (200, 201)

        follow_up = api_client.get_booking(booking_id)
        assert follow_up.status_code == 404

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_delete_of_a_nonexistent_booking_returns_404(self, api_client, auth_headers):
        response = api_client.delete_booking(999_999_999, headers=auth_headers)

        assert response.status_code == 404, (
            "BUG-007: DELETE on a non-existent booking id returns 405 Method "
            f"Not Allowed instead of 404 Not Found (got {response.status_code})"
        )
