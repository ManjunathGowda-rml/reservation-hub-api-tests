import allure
import pytest
from requests.auth import HTTPBasicAuth

from config import AUTH_PASSWORD, AUTH_USERNAME
from data.booking_factory import build_booking


@allure.feature("Authentication")
@pytest.mark.auth
class TestAuth:
    @allure.severity(allure.severity_level.CRITICAL)
    def test_valid_credentials_return_a_token(self, api_client):
        response = api_client.auth(AUTH_USERNAME, AUTH_PASSWORD)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body.get("token"), str) and body["token"]

    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.negative
    def test_invalid_credentials_are_rejected_with_401(self, api_client):
        """A correct auth endpoint signals failure via status code - a
        client that only checks `response.ok` should not be able to
        mistake a rejected login for a successful one.
        """
        response = api_client.auth(AUTH_USERNAME, "definitely-wrong-password")

        assert response.status_code == 401, (
            "BUG-006: POST /auth returns 200 OK with a "
            "{'reason': 'Bad credentials'} body for invalid credentials "
            f"instead of 401 Unauthorized (got {response.status_code})"
        )


@allure.feature("Authorization")
@pytest.mark.auth
class TestWriteAuthorization:
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.parametrize("verb", ["PUT", "PATCH", "DELETE"])
    def test_write_operations_are_rejected_without_auth(self, api_client, new_booking, verb):
        booking_id, _, _ = new_booking

        if verb == "PUT":
            response = api_client.update_booking(booking_id, build_booking())
        elif verb == "PATCH":
            response = api_client.partial_update_booking(booking_id, {"totalprice": 1})
        else:
            response = api_client.delete_booking(booking_id)

        assert response.status_code == 403

    @allure.severity(allure.severity_level.BLOCKER)
    def test_write_operation_is_rejected_with_an_invalid_token(self, api_client, new_booking):
        booking_id, _, _ = new_booking

        response = api_client.update_booking(
            booking_id, build_booking(), headers=api_client.cookie_header("not-a-real-token")
        )

        assert response.status_code == 403

    @allure.severity(allure.severity_level.NORMAL)
    def test_http_basic_auth_is_accepted_as_an_alternative_to_the_cookie_token(self, api_client, new_booking):
        booking_id, _, _ = new_booking

        response = api_client.partial_update_booking(
            booking_id, {"totalprice": 321}, auth=HTTPBasicAuth(AUTH_USERNAME, AUTH_PASSWORD)
        )

        assert response.status_code == 200
        assert response.json()["totalprice"] == 321
