"""Central configuration for the Reservation Hub API test suite.

Everything here can be overridden with an environment variable so the same
suite can be pointed at a different environment (e.g. a staging deploy of
Reservation Hub) without touching test code.
"""
import os

BASE_URL = os.environ.get("RESERVATION_HUB_BASE_URL", "https://restful-booker.herokuapp.com")

AUTH_USERNAME = os.environ.get("RESERVATION_HUB_USERNAME", "admin")
AUTH_PASSWORD = os.environ.get("RESERVATION_HUB_PASSWORD", "password123")

# The sandbox runs on a free Heroku dyno that can take 20-30s to wake from a
# cold start, so the read timeout is generous on purpose.
CONNECT_TIMEOUT_SECONDS = float(os.environ.get("RESERVATION_HUB_CONNECT_TIMEOUT", 10))
READ_TIMEOUT_SECONDS = float(os.environ.get("RESERVATION_HUB_READ_TIMEOUT", 30))
REQUEST_TIMEOUT = (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)

MAX_RETRY_ATTEMPTS = int(os.environ.get("RESERVATION_HUB_MAX_RETRIES", 5))
RETRY_MIN_WAIT_SECONDS = 1
RETRY_MAX_WAIT_SECONDS = 15
