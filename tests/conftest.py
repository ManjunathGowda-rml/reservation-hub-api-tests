import json
import logging
import os

import allure
import pytest

from api.client import BookingApiClient
from config import AUTH_PASSWORD, AUTH_USERNAME, BASE_URL
from data.booking_factory import build_booking

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def api_client():
    return BookingApiClient(base_url=BASE_URL)


@pytest.fixture(scope="session", autouse=True)
def _wait_for_api_ready(api_client):
    """Ping once before the suite runs so cold-start latency shows up here,
    as one clearly-labelled step, instead of making the first real test
    look slow or flaky. BookingApiClient itself also retries on
    connection errors/timeouts and 502/503/504 on every call.
    """
    with allure.step("Wait for API to be ready (cold-start handling)"):
        response = api_client.ping()
        assert response.status_code == 201, f"API did not respond to /ping: {response.status_code}"


@pytest.fixture(scope="session")
def admin_token(api_client):
    response = api_client.auth(AUTH_USERNAME, AUTH_PASSWORD)
    assert response.status_code == 200, "Failed to obtain admin auth token"
    token = response.json().get("token")
    assert token, "Auth response did not contain a token"
    return token


@pytest.fixture
def auth_headers(api_client, admin_token):
    return api_client.cookie_header(admin_token)


@pytest.fixture
def new_booking(api_client, admin_token):
    """Creates a fresh, uniquely-named booking and cleans it up afterwards.

    Cleanup is best-effort: the sandbox resets its data to the default 10
    records roughly every 10 minutes, so the booking may already be gone by
    teardown time - that's expected, not a test failure.
    """
    payload = build_booking()
    response = api_client.create_booking(payload)
    assert response.status_code == 200, f"Setup failed: could not create booking ({response.status_code})"
    booking_id = response.json()["bookingid"]

    yield booking_id, payload, response.json()

    try:
        api_client.delete_booking(booking_id, headers=api_client.cookie_header(admin_token))
    except Exception as exc:  # pragma: no cover - best-effort cleanup
        logger.warning("Cleanup for booking %s skipped (likely already reset): %s", booking_id, exc)


def pytest_sessionfinish(session, exitstatus):
    """Write Allure environment info + a categories.json that buckets our
    intentionally-red "known defect" assertions (see BUGS.md) separately
    from genuine test failures, so the report summary stays honest instead
    of looking like a broken suite.
    """
    alluredir = session.config.getoption("allure_report_dir", default=None)
    if not alluredir:
        return
    os.makedirs(alluredir, exist_ok=True)

    with open(os.path.join(alluredir, "environment.properties"), "w") as f:
        f.write(f"Base_URL={BASE_URL}\n")
        f.write("System_under_test=Reservation Hub Bookings API (restful-booker sandbox)\n")

    categories = [
        {
            "name": "Known product defects (see BUGS.md)",
            "matchedStatuses": ["failed"],
            "messageRegex": "(?s).*BUG-\\d+:.*",
        },
        {
            "name": "Test infrastructure issues",
            "matchedStatuses": ["broken"],
        },
        {
            # Allure categories aren't first-match-wins - a failure matches every
            # category whose regex matches, so this one must positively exclude
            # anything already tagged BUG-xxx above, or every known defect would
            # also show up here.
            "name": "Unexpected failures",
            "matchedStatuses": ["failed"],
            "messageRegex": "(?s)((?!BUG-\\d+:).)*",
        },
    ]
    with open(os.path.join(alluredir, "categories.json"), "w") as f:
        json.dump(categories, f, indent=2)
