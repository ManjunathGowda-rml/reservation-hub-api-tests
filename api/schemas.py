"""JSON Schemas for the Bookings API response contracts, plus a small
assertion helper that turns a jsonschema ValidationError into a readable
pytest assertion failure instead of a raw traceback.
"""
from jsonschema import FormatChecker, ValidationError, validate

BOOKING_SCHEMA = {
    "type": "object",
    "required": ["firstname", "lastname", "totalprice", "depositpaid", "bookingdates"],
    "additionalProperties": True,
    "properties": {
        "firstname": {"type": "string", "minLength": 1},
        "lastname": {"type": "string", "minLength": 1},
        "totalprice": {"type": "number"},
        "depositpaid": {"type": "boolean"},
        "bookingdates": {
            "type": "object",
            "required": ["checkin", "checkout"],
            "properties": {
                "checkin": {"type": "string", "format": "date"},
                "checkout": {"type": "string", "format": "date"},
            },
        },
        "additionalneeds": {"type": "string"},
    },
}

CREATE_BOOKING_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["bookingid", "booking"],
    "properties": {
        "bookingid": {"type": "integer"},
        "booking": BOOKING_SCHEMA,
    },
}

BOOKING_ID_LIST_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["bookingid"],
        "properties": {"bookingid": {"type": "integer"}},
    },
}

AUTH_TOKEN_SCHEMA = {
    "type": "object",
    "required": ["token"],
    "properties": {"token": {"type": "string", "minLength": 1}},
}


def assert_matches_schema(instance, schema):
    try:
        validate(instance=instance, schema=schema, format_checker=FormatChecker())
    except ValidationError as exc:
        raise AssertionError(f"Response does not match expected schema: {exc.message}") from exc
