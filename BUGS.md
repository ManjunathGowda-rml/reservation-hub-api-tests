# Bug Report — Reservation Hub Bookings API

Found while building the automated regression suite in this repo. Every
bug below has a failing, automated test that reproduces it (see the
"Automated test" column) — run `./run_tests.sh` and check `report.html` or
the Allure "Known product defects" category for live confirmation.

Severity scale: **Critical** (data integrity / directly matches the
production incident) → **High** (bad input silently accepted or corrupted)
→ **Medium** (wrong error class, but the request is at least rejected) →
**Low** (wrong status code / misleading response, no data impact).

---

## BUG-001 — `POST /booking` accepts a negative `totalprice`

**Severity: Critical.** This is the exact incident from the brief: a
booking can be created with a negative price, silently, with a 200 OK.

**Steps to reproduce**

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Neg","lastname":"Price","totalprice":-500,"depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'
```

**Expected:** `400 Bad Request`, no booking created, an error body naming
the invalid field.

**Actual:** `200 OK`. Booking is created with `totalprice: -500` and a
valid `bookingid`.

**Automated test:** `tests/test_negative_and_boundary.py::test_negative_total_price_is_rejected`

---

## BUG-002 — `POST /booking` accepts a `checkout` date before `checkin`

**Severity: Critical.** The other half of the incident from the brief: a
booking date range that is logically inverted is accepted as-is.

**Steps to reproduce**

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Bad","lastname":"Dates","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"2026-05-05","checkout":"2026-01-01"}}'
```

**Expected:** `400 Bad Request` — checkout must not precede checkin.

**Actual:** `200 OK`. Booking is created with `checkin: 2026-05-05,
checkout: 2026-01-01`.

**Automated test:** `tests/test_negative_and_boundary.py::test_checkout_before_checkin_is_rejected`

---

## BUG-003 — Wrong-typed `totalprice` is silently coerced to `null` and stored

**Severity: High.** This is worse than simply ignoring bad input: the
server accepts a non-numeric price and *silently* replaces it with `null`
instead of rejecting the request, corrupting the record without any
signal to the caller.

**Steps to reproduce**

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Str","lastname":"Price","totalprice":"one hundred","depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'
```

**Expected:** `400 Bad Request` — `totalprice` must be numeric.

**Actual:** `200 OK`. Response body shows `"totalprice": null` — the
booking exists in a state that violates its own schema.

**Automated test:** `tests/test_negative_and_boundary.py::test_non_numeric_total_price_is_rejected`

---

## BUG-004 — Malformed `checkin` date is silently corrupted and stored

**Severity: High.** Same class of bug as BUG-003, applied to dates: an
unparseable date string isn't rejected, it's converted into garbage and
persisted.

**Steps to reproduce**

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Mal","lastname":"Formed","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"not-a-date","checkout":"2026-01-05"}}'
```

**Expected:** `400 Bad Request` — `checkin` must be a valid ISO date.

**Actual:** `200 OK`. Response shows `"checkin": "0NaN-aN-aN"` — an
invalid `Date` object was serialized straight into the stored record.

**Automated test:** `tests/test_negative_and_boundary.py::test_malformed_checkin_date_is_rejected`

---

## BUG-005 — Missing required fields cause a `500`, not a `400`

**Severity: Medium.** The request is at least not silently accepted, but a
missing/empty body should be the textbook case for `400 Bad Request`, not
an unhandled server exception. A `500` gives an API consumer nothing to
act on and may leak implementation details in server logs.

**Steps to reproduce**

```bash
# missing "firstname"
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"lastname":"NoFirst","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'

# empty payload
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" -d '{}'
```

**Expected:** `400 Bad Request` naming the missing field(s).

**Actual:** `500 Internal Server Error` for any of `firstname`,
`lastname`, `totalprice`, `depositpaid`, `bookingdates` missing, or an
empty `{}` body.

**Automated test:** `tests/test_negative_and_boundary.py::test_missing_required_field_is_rejected_with_400`
(parametrized over all five required fields) and
`::test_empty_payload_is_rejected_with_400`.

---

## BUG-006 — `POST /auth` returns `200 OK` for invalid credentials

**Severity: Low.** No data is at risk, but the contract is misleading: any
caller that checks `response.ok` / status code alone (a very common
pattern) instead of inspecting the body will treat a rejected login as a
success.

**Steps to reproduce**

```bash
curl -i -X POST https://restful-booker.herokuapp.com/auth \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong-password"}'
```

**Expected:** `401 Unauthorized`.

**Actual:** `200 OK` with body `{"reason":"Bad credentials"}`.

**Automated test:** `tests/test_auth.py::TestAuth::test_invalid_credentials_are_rejected_with_401`

---

## BUG-007 — `PUT`/`DELETE` on a non-existent booking id returns `405`, not `404`

**Severity: Low.** Cosmetic/contract issue, no data impact, but `405
Method Not Allowed` is semantically wrong here (the method itself is
allowed on the route — the *resource* doesn't exist) and will confuse API
consumers doing status-code-based error handling.

**Steps to reproduce**

```bash
TOKEN=$(curl -s -X POST https://restful-booker.herokuapp.com/auth \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password123"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -i -X DELETE https://restful-booker.herokuapp.com/booking/999999999 \
  -H "Cookie: token=$TOKEN"

curl -i -X PUT https://restful-booker.herokuapp.com/booking/999999999 \
  -H "Content-Type: application/json" -H "Cookie: token=$TOKEN" \
  -d '{"firstname":"Ghost","lastname":"Booking","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'
```

**Expected:** `404 Not Found` for both.

**Actual:** `405 Method Not Allowed` for both.

**Automated tests:**
`tests/test_delete_booking.py::test_delete_of_a_nonexistent_booking_returns_404`,
`tests/test_update_booking.py::test_put_on_a_nonexistent_booking_returns_404`
