# Bug Report — Reservation Hub Bookings API

Found while building the automated regression suite in this repo. Every
bug below has a failing, automated test that reproduces it — run
`./run_tests.sh` and check `report.html` for live confirmation.

Severity: **Critical** (data integrity / matches the production incident)
→ **High** (bad input silently accepted or corrupted) → **Medium** (wrong
error class, request at least rejected) → **Low** (wrong status code /
misleading response, no data impact).

---

## BUG-001 — `POST /booking` accepts a negative `totalprice`

**Critical.** The exact incident from the brief: a booking can be created
with a negative price, silently, with a 200 OK.

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Neg","lastname":"Price","totalprice":-500,"depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'
```

**Expected:** `400 Bad Request`. **Actual:** `200 OK`, booking created
with `totalprice: -500`.

**Test:** `tests/test_negative_and_boundary.py::test_negative_total_price_is_rejected`

---

## BUG-002 — `POST /booking` accepts a `checkout` date before `checkin`

**Critical.** The other half of the incident: an inverted date range is
accepted as-is.

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Bad","lastname":"Dates","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"2026-05-05","checkout":"2026-01-01"}}'
```

**Expected:** `400 Bad Request`. **Actual:** `200 OK`, booking created
with `checkin` after `checkout`.

**Test:** `tests/test_negative_and_boundary.py::test_checkout_before_checkin_is_rejected`

---

## BUG-003 — Wrong-typed `totalprice` is silently coerced to `null` and stored

**High.** Worse than ignoring bad input: the server accepts a non-numeric
price and silently replaces it with `null`, corrupting the record without
any signal to the caller.

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Str","lastname":"Price","totalprice":"one hundred","depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'
```

**Expected:** `400 Bad Request`. **Actual:** `200 OK`, response shows
`"totalprice": null`.

**Test:** `tests/test_negative_and_boundary.py::test_non_numeric_total_price_is_rejected`

---

## BUG-004 — Malformed `checkin` date is silently corrupted and stored

**High.** Same class as BUG-003, for dates: an unparseable date string is
converted into garbage and persisted instead of rejected.

```bash
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"firstname":"Mal","lastname":"Formed","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"not-a-date","checkout":"2026-01-05"}}'
```

**Expected:** `400 Bad Request`. **Actual:** `200 OK`, response shows
`"checkin": "0NaN-aN-aN"`.

**Test:** `tests/test_negative_and_boundary.py::test_malformed_checkin_date_is_rejected`

---

## BUG-005 — Missing required fields cause a `500`, not a `400`

**Medium.** At least not silently accepted, but a missing/empty body
should be a textbook `400`, not an unhandled server exception (which
gives a caller nothing to act on and may leak implementation details).

```bash
# missing "firstname"
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" \
  -d '{"lastname":"NoFirst","totalprice":100,"depositpaid":true,"bookingdates":{"checkin":"2026-01-01","checkout":"2026-01-05"}}'

# empty payload
curl -i -X POST https://restful-booker.herokuapp.com/booking \
  -H "Content-Type: application/json" -d '{}'
```

**Expected:** `400 Bad Request` naming the missing field. **Actual:** `500
Internal Server Error` for any of the 5 required fields missing, or `{}`.

**Test:** `tests/test_negative_and_boundary.py::test_missing_required_field_is_rejected_with_400`
(parametrized over all five required fields) and `::test_empty_payload_is_rejected_with_400`.

---

## BUG-006 — `POST /auth` returns `200 OK` for invalid credentials

**Low.** No data at risk, but any caller that checks status code alone
(a common pattern) will treat a rejected login as a success.

```bash
curl -i -X POST https://restful-booker.herokuapp.com/auth \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"wrong-password"}'
```

**Expected:** `401 Unauthorized`. **Actual:** `200 OK` with body
`{"reason":"Bad credentials"}`.

**Test:** `tests/test_auth.py::TestAuth::test_invalid_credentials_are_rejected_with_401`

---

## BUG-007 — `PUT`/`DELETE` on a non-existent booking id returns `405`, not `404`

**Low.** Cosmetic, no data impact, but `405 Method Not Allowed` is
semantically wrong (the method is allowed on the route — the *resource*
doesn't exist), and will confuse status-code-based error handling.

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

**Expected:** `404 Not Found` for both. **Actual:** `405 Method Not
Allowed` for both.

**Tests:**
`tests/test_delete_booking.py::test_delete_of_a_nonexistent_booking_returns_404`,
`tests/test_update_booking.py::test_put_on_a_nonexistent_booking_returns_404`
