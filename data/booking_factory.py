"""Test data builders for the Bookings API.

The sandbox is a shared instance already holding hundreds of bookings from
other people running this same exercise, so every booking we create gets a
unique name - that keeps name-filter assertions (`test_read_booking.py`)
honest and stops one run's data from being mistaken for another's.
"""
import uuid


def _unique(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def build_booking(**overrides):
    """A valid booking payload. Pass keyword overrides to change individual
    top-level fields, e.g. build_booking(totalprice=-1) or
    build_booking(bookingdates={"checkin": "2026-01-01", "checkout": "2026-01-05"}).
    """
    booking = {
        "firstname": _unique("Guest"),
        "lastname": _unique("Tester"),
        "totalprice": 150,
        "depositpaid": True,
        "bookingdates": {
            "checkin": "2026-06-01",
            "checkout": "2026-06-05",
        },
        "additionalneeds": "Breakfast",
    }
    booking.update(overrides)
    return booking
