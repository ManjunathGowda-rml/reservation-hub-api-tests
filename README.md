# Reservation Hub — Bookings API regression suite

Automated API test suite for the Bookings API of "Reservation Hub", run
against the public `restful-booker` sandbox
(`https://restful-booker.herokuapp.com`).

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./run_tests.sh
```

That runs the whole suite and writes `report.html` — a single
self-contained file, open it directly in a browser.

Run a subset with normal pytest marker/keyword filtering, e.g.
`pytest -m negative` or `pytest -k update_booking`.

## Project layout

```
config.py                    base URL, credentials, timeouts - env-overridable
api/client.py                BookingApiClient: the only place that calls `requests`
api/schemas.py                JSON Schemas for response contracts + assertion helper
data/booking_factory.py      builds valid/overridden booking payloads with unique names
tests/conftest.py            fixtures: api_client, admin_token, new_booking, cold-start wait
tests/test_auth.py           token retrieval, write-endpoint authorization
tests/test_create_booking.py happy-path create + contract validation
tests/test_read_booking.py   get by id, list, filters, 404
tests/test_update_booking.py PUT (full) and PATCH (partial) happy paths
tests/test_delete_booking.py delete + verify gone
tests/test_negative_and_boundary.py  bad input handling - see "Test strategy" below
BUGS.md                      defects found, with curl repro and severity
```

## Test strategy

Every endpoint in scope has a happy-path test that asserts on the full
response body (`response.json() == payload`), not just the status code.
On top of that:

- **`test_auth.py`** checks that `PUT`/`PATCH`/`DELETE` are actually
  rejected without a valid credential — tested three ways (no auth,
  garbage token, HTTP Basic Auth) since "write protection" is easy to get
  half right (e.g. enforced on `PUT` but not `PATCH`).
- **`test_negative_and_boundary.py`** is the regression suite for the
  incident this exercise is about: `test_negative_total_price_is_rejected`
  and `test_checkout_before_checkin_is_rejected` are the two conditions
  from the incident, written as if the API were correct.

**A deliberate, non-standard choice:** those input-validation tests assert
the *correct* expected behaviour (e.g. `400 Bad Request` for a negative
price), not the sandbox's actual behaviour. Since the sandbox genuinely
has no input validation, **13 of the 29 tests fail by design** — that's
intentional, not a broken suite. Each failing assertion message is
prefixed with a `BUG-xxx` id (e.g. `"BUG-001: POST /booking accepts a
negative totalprice..."`) so it's identifiable at a glance in
`report.html` or the pytest output; see [BUGS.md](BUGS.md) for the full
list with repro steps.

I considered `pytest.mark.xfail` instead, which would keep the suite
green, but that reads as "we expect this to be broken and that's fine" —
undersells exactly the kind of bug this exercise is about. A loud,
labelled failure is the more honest signal.

**Response contracts:** `api/schemas.py` has JSON Schemas for the booking
object, the create-booking response, and the booking-id list, validated
via `jsonschema` in the happy-path tests. This catches shape regressions
(wrong type, missing field) that a field-by-field assertion could miss.

**Deliberately left out:** exhaustive type-sweeps across every field
(only `totalprice`/`checkin` — the two fields the incident was about —
get dedicated bad-type tests); `GET /booking` date-filter edge cases;
concurrency/performance testing; contract testing beyond JSON Schema.

## Handling the shared, self-resetting sandbox

Two properties of this environment shape the design:

1. **It's shared and never empty.** `data/booking_factory.py` gives every
   created booking a `uuid4`-suffixed name (`Guest-3f9a1c2b`) so
   name-filter tests can never collide with someone else's data, and no
   test depends on the total record count or on any pre-existing id.
2. **It resets on its own timer (~10 min), independent of test runs.**
   Every test that creates data cleans up in its own teardown, but that
   cleanup is best-effort and swallows errors — the booking may already
   be gone by teardown time. The only place a "random" pre-existing id is
   used is the two `..._nonexistent_id` tests, which use `999999999`
   specifically because it's outside any id range the sandbox has ever
   generated..

**Cold starts:** the free Heroku dyno can take 20-30s to wake up.
`BookingApiClient._request` retries with exponential backoff (via
`tenacity`) on connection errors/timeouts and on `502`/`503`/`504`
specifically — not on `500`, since a `500` here is a real (buggy)
response we need to assert on, not a transient failure to paper over. A
session-scoped fixture also pings once before any test runs, so wake-up
latency doesn't make whichever test runs first look slow or flaky.

## Known limitations

- The suite runs sequentially against a shared sandbox; if the ~10-minute
  reset lands mid-run, a test relying on state from an earlier step in
  the same run could fail. Not hit in practice, but a real limitation of
  testing against a shared, autonomously-resetting environment.
- `GET /booking` filter semantics (date filters look like a range/overlap
  match rather than exact match) are used but not independently verified.
- No load/concurrency testing.
