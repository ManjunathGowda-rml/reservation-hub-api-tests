"""Thin HTTP client for the Reservation Hub Bookings API.

Test modules should never call `requests` directly - going through this
client keeps the base URL, timeouts, cold-start retries and
request/response logging in one place instead of scattered across tests.
"""
import logging

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import (
    BASE_URL,
    MAX_RETRY_ATTEMPTS,
    RETRY_MAX_WAIT_SECONDS,
    RETRY_MIN_WAIT_SECONDS,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)

# 502/503/504 from Heroku's router are the signature of a dyno still waking
# up from a cold start - worth a retry. A 500 from the app itself (e.g. the
# "missing field" bug) is a real response and must NOT be retried away.
_COLD_START_STATUS_CODES = {502, 503, 504}


class TransientApiError(Exception):
    """Raised for gateway-level responses that look like a cold start."""


def _log_request_response(response):
    request = response.request
    body = request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")

    lines = [f"{request.method} {request.url}"]
    if body:
        lines.append(f"Request body: {body}")
    lines.append(f"Status: {response.status_code}")
    lines.append(f"Response body: {response.text}")

    logger.debug("\n".join(lines))


class BookingApiClient:
    def __init__(self, base_url=BASE_URL, session=None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    @retry(
        retry=retry_if_exception_type(
            (requests.exceptions.ConnectionError, requests.exceptions.Timeout, TransientApiError)
        ),
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(min=RETRY_MIN_WAIT_SECONDS, max=RETRY_MAX_WAIT_SECONDS),
        reraise=True,
    )
    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", REQUEST_TIMEOUT)
        response = self.session.request(method, url, **kwargs)
        if response.status_code in _COLD_START_STATUS_CODES:
            raise TransientApiError(
                f"{method} {url} returned {response.status_code}, retrying (cold start?)"
            )
        _log_request_response(response)
        return response

    # --- health ---------------------------------------------------------
    def ping(self):
        return self._request("GET", "/ping")

    # --- auth -------------------------------------------------------------
    def auth(self, username, password):
        return self._request("POST", "/auth", json={"username": username, "password": password})

    @staticmethod
    def cookie_header(token):
        return {"Cookie": f"token={token}"}

    # --- bookings ---------------------------------------------------------
    def create_booking(self, payload):
        return self._request("POST", "/booking", json=payload)

    def get_booking_ids(self, **filters):
        return self._request("GET", "/booking", params=filters)

    def get_booking(self, booking_id):
        return self._request("GET", f"/booking/{booking_id}")

    def update_booking(self, booking_id, payload, **auth_kwargs):
        return self._request("PUT", f"/booking/{booking_id}", json=payload, **auth_kwargs)

    def partial_update_booking(self, booking_id, payload, **auth_kwargs):
        return self._request("PATCH", f"/booking/{booking_id}", json=payload, **auth_kwargs)

    def delete_booking(self, booking_id, **auth_kwargs):
        return self._request("DELETE", f"/booking/{booking_id}", **auth_kwargs)
