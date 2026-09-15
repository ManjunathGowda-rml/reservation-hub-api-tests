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

That runs the whole suite and regenerates both reports:

- `report.html` — single self-contained file, open it directly in a browser.
- `allure-report/` — the richer, navigable report. Because of browser XHR
  restrictions it needs to be served, not opened via `file://`:
  `allure open allure-report`, or `python3 -m http.server -d allure-report`.

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

**What's covered, and why:** every endpoint in scope gets at least one
happy-path test asserting on the full response body, not just the status
code (`response.json() == payload`, not `response.status_code == 200`).
On top of that, the suite is weighted toward the two risks the brief
calls out directly:

- **Auth/authorization** (`test_auth.py`): a token can be obtained, and —
  more important for a booking platform — `PUT`/`PATCH`/`DELETE` are
  actually rejected without a valid credential. This is asserted three
  ways (no auth, garbage token, and the alternate HTTP Basic Auth mode)
  because "write protection" is the kind of thing that's easy to get half
  right (e.g. enforced on `PUT` but not `PATCH`).
- **Input validation** (`test_negative_and_boundary.py`): this is the
  direct regression suite for the incident in the brief. It doesn't just
  probe generic "bad input" — `test_negative_total_price_is_rejected` and
  `test_checkout_before_checkin_is_rejected` are literally the two
  conditions from the incident, written as if the API were correct.

**A deliberate, non-standard choice:** those input-validation tests
assert the *correct* expected behaviour (e.g. `400 Bad Request` for a
negative price), not the sandbox's actual behaviour. Since the sandbox
genuinely has no input validation, **13 of the 29 tests fail by design**.
That's intentional, not a broken suite — see [BUGS.md](BUGS.md) for the
full list. Each failing assertion message is prefixed with a `BUG-xxx` id
(e.g. `"BUG-001: POST /booking accepts a negative totalprice..."`), and
`conftest.py` writes an Allure `categories.json` that buckets every
`BUG-xxx` failure under **"Known product defects (see BUGS.md)"**, kept
separate from a catch-all **"Unexpected failures"** category. So the
report's headline pass/fail count stays honest (16 passed / 13 known
defects, not "13 broken tests"), while a partner-facing dashboard would
still show red for as long as these are unfixed — which is exactly what a
safety net for this incident should do. If a test in that category ever
turns green, that's a real signal the underlying bug was fixed and the
assertion can be promoted out of the "known defect" framing.

I considered `pytest.mark.xfail` instead, which would keep the suite
green. I didn't use it: `xfail` reads, at a glance, as "we expect this to
be broken and that's fine," which undersells exactly the kind of bug this
exercise is about. A loud, categorized, well-labelled failure is the more
honest signal here.

**Response contracts:** `api/schemas.py` has JSON Schemas for the booking
object, the create-booking response, and the booking-id list, validated
via `jsonschema` in the happy-path tests (`test_create_booking.py`,
`test_read_booking.py`, `test_update_booking.py`). This catches shape
regressions (wrong type, missing field) that a field-by-field assertion
could miss.

**What I deliberately left out, and why:**

- *Exhaustive boundary sweeps* (every field × every invalid type) —
  `test_missing_required_field_is_rejected_with_400` is parametrized
  across all five required fields to avoid copy-paste, but I didn't do
  the same for "wrong type" across every field; `totalprice` and
  `checkin` are the two fields the incident was about, so those get
  dedicated tests and the rest didn't seem worth the volume for this
  exercise ("twenty thoughtful tests over two hundred shallow ones").
- *Query-filter edge cases* for `GET /booking` (e.g. `checkin`/`checkout`
  range-vs-exact semantics) — filtering is exercised by name, which is
  what the rest of the suite actually depends on; a deeper investigation
  of the date-filter semantics felt like a separate mini-project rather
  than a gap in the safety net.
- *Concurrency / performance* — out of scope for this exercise; noted as
  a bonus idea below.
- *Contract testing beyond JSON Schema* (Pact, OpenAPI) — there's no
  OpenAPI spec published for this sandbox to validate against, and a full
  consumer-driven contract suite is disproportionate for a single
  read-only public sandbox.

## Handling the shared, self-resetting sandbox

Two properties of this environment shape the design:

1. **It's shared and never empty.** At the time of writing the sandbox
   already had 800+ bookings from other people running this same
   exercise, well past its documented "10 records." `data/booking_factory.py`
   gives every created booking a `uuid4`-suffixed name
   (`Guest-3f9a1c2b`) so tests that filter by name can never collide with
   someone else's data, and no test depends on the total record count or
   on any of the original seed IDs.
2. **It resets on its own timer (~10 min), independent of test runs.**
   Every test that creates data does so itself (the `new_booking`
   fixture) and cleans up in its own teardown — but that cleanup is
   best-effort and swallows errors, because the booking may have already
   vanished in a reset between setup and teardown. Nothing in the suite
   asserts on a fixed pre-existing booking id; the only place a "random"
   pre-existing id is used is the two `..._nonexistent_id` tests, which
   use `999999999` specifically because it's outside any id range the
   sandbox has ever generated.

**Cold starts:** the free Heroku dyno can take 20-30s to wake up.
`BookingApiClient._request` retries with exponential backoff (via
`tenacity`) on connection errors/timeouts and on `502`/`503`/`504`
specifically — not on `500`, since a `500` here is a real (buggy)
response we need to assert on, not a transient failure to paper over. A
session-scoped `_wait_for_api_ready` fixture also pings once before any
test runs, so the wake-up latency shows up as one clearly-labelled
"Wait for API to be ready" step instead of making whichever test happens
to run first look slow or flaky.

## Known limitations

- The suite runs sequentially against a shared sandbox; if the ~10-minute
  reset happens to land mid-run, a test relying on state from an earlier
  step in the same run (e.g. `test_created_booking_can_be_read_back_unchanged`)
  could fail. I didn't hit this in practice, but it's a real limitation of
  testing against a fully shared, autonomously-resetting environment
  rather than an isolated instance.
- `GET /booking` filter semantics (date filters look like a range/overlap
  match rather than exact match) are used but not independently verified
  — see "What I deliberately left out" above.
- No load/concurrency testing (see bonus ideas below).

## Bonus ideas not implemented (given the time box)

- A handful of concurrent `POST /booking` calls to check for id
  collisions or race conditions under load, with p50/p95 latency logged —
  useful signal before scaling traffic, not attempted here.
- Publishing an OpenAPI spec for this API (none exists today) and
  validating every response against it automatically, rather than the
  hand-written JSON Schemas in `api/schemas.py`.
