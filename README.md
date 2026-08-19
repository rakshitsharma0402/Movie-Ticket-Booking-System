# Movie Tickets Booking (MTBX)

A Frappe app for browsing movies, scheduling shows, and booking tickets — built end-to-end as a developer training assessment, covering DocTypes, server-side controllers, client scripts, whitelisted APIs, role-based permissions, a public web portal, scheduled jobs, hooks, a Script Report, data migration patches, unit tests, and a handful of bonus features.

- **Framework:** Frappe (bench app name: `movietickets`)
- **Local dev site:** `cinema.localhost`
- **Python module for DocTypes:** `movietickets/movie_ticket_booking/doctype/...`
- **Top-level app files:** `movietickets/hooks.py`, `movietickets/api.py`, `movietickets/tasks.py`

---

## Setup

```bash
bench init cinema-bench --frappe-branch version-16
bench new-site cinema.localhost
bench new-app movietickets
bench --site cinema.localhost install-app movietickets
bench use cinema.localhost
bench start
```

Visit `http://cinema.localhost:8000` and log in as Administrator.

### Dependencies

QR code generation (bonus feature) requires:

```bash
./env/bin/pip install qrcode[pil] --break-system-packages
```

Also listed in `movietickets/requirements.txt`.

---

## Data Model

| DocType | Purpose |
|---|---|
| Movie Genre | Lookup table for genres, case-insensitive unique names |
| Movie | Catalog entry — title, language, genre, duration, dates, rating, auto-slug, auto-status |
| Theater | Cinema location — auto-named `"{theater_name} - {city}"`, auto-calculated `total_screens` |
| Screen | Individual screen within a theater — auto-named `"{theater_name}-{screen_name}"`, seat-math validated |
| Show | A scheduled screening — computed `end_time`, defaulted `ticket_price`, conflict-checked against overlapping shows |
| Ticket Booking | Submittable transactional booking — customer info, seats, pricing, refund handling |
| Booked Seat | Child table of Ticket Booking — individual seat rows with per-seat price override support |
| Booking Configuration | Single DocType — central settings (seat limits, expiry window, refund thresholds) |

---

## Business Logic Highlights

- **Seat labeling:** rows are lettered A–Z (row 1 = A, row 2 = B, …), capped at 26 rows across both the booking controller and the seat-availability API.
- **Two distinct cancellation paths:**
  - *Organization-initiated* (`Show.show_status → Cancelled`): flat 100% refund to all affected bookings, applied via direct field updates — customers aren't penalized for a decision that wasn't theirs.
  - *Customer-initiated* (`Ticket Booking.cancel()`): tiered refund based on Booking Configuration thresholds (full refund >4h before show, 50% between 2–4h, 0% under 2h).
- **Race-condition-safe booking creation:** `create_booking` locks the Show document (`Document.lock()`/`.unlock()`) around seat re-validation and insert, preventing two customers from grabbing the same seat concurrently.
- **Known inconsistency (flagged, not fixed):** `Ticket Booking.total_amount` uses a flat `number_of_seats × price_per_seat` formula and does **not** sum individual `Booked Seat.seat_price` overrides, even though the schema supports premium per-seat pricing. The Box Office Collection Report and dashboard deliberately sum `seat_price` directly instead, so their revenue figures may legitimately diverge from `total_amount`-based figures (e.g. MTBX-8.5's revenue API). This is a candidate for a follow-up fix.

---

## Whitelisted APIs (`movietickets/api.py`)

| Function | Access | Purpose |
|---|---|---|
| `get_seat_availability(show_name)` | Authenticated | Seat grid with per-seat booked/available status |
| `create_booking(show, customer_name, customer_email, customer_phone, seats)` | Authenticated | Race-condition-safe booking creation |
| `get_shows_for_movie(movie, city=None, date=None)` | Guest | Upcoming shows for a movie, portal-facing |
| `send_booking_confirmation(booking_name)` | Authenticated | HTML confirmation email with embedded QR code |
| `get_revenue_summary(theater=None, from_date=None, to_date=None)` | Authenticated | Aggregate revenue/occupancy stats |
| `create_shows_bulk(movie, screens, date_from, date_to, show_times)` | Authenticated | Enqueues bulk Show creation as a background job |

Dashboard chart data endpoints (`get_todays_occupancy_by_theater`, `get_revenue_trend_30_days`, `get_bookings_by_time_slot`, `get_top_5_movies_by_bookings`) also live here.

---

## Web Portal

| Page | Access | Description |
|---|---|---|
| `/now-showing` | Guest | Card grid of Now Showing movies, genre/language filters |
| `/movie-shows?movie=MOV-XXXXX` | Guest (viewing) / Login (booking) | Shows grouped by theater and date, "Book Now" |
| `/my-bookings` | Login required | Logged-in user's booking history with status badges |

> **Known gap:** the actual seat-selection/booking-creation portal page (where "Book Now" should lead once logged in) is not built — flagged during MTBX-10.2 as a likely missing ticket.

---

## Roles & Permissions

| Role | Access |
|---|---|
| Cinema Manager | Full CRUD + submit/cancel on all DocTypes |
| Box Office Staff | Create/submit/cancel bookings; read-only on Movie/Theater/Screen/Show |
| Customer | Create bookings (own only); read-only Movie/Show; no Theater/Screen access; portal-only (no Desk access) |

Row-level restriction is enforced via a `has_permission` hook on Ticket Booking, limiting Customer-role users to `booked_by == session user`.

Test users: `manager@test.com`, `staff@test.com`, `customer@test.com`.

---

## Scheduled Jobs (`movietickets/tasks.py`)

| Job | Schedule | Purpose |
|---|---|---|
| `expire_stale_bookings` | Every 5 min (cron) | Expires stale Pending/Unpaid bookings, releases seats |
| `update_movie_status` | Daily | Recalculates `movie_status` for all movies |
| `update_show_status` | Hourly | Transitions shows through Now Playing → Completed |
| `send_daily_revenue_digest` | Daily at 23:00 (cron) | Emails Cinema Managers a summary of the day's bookings/revenue |

> **Known limitation:** `update_show_status` relies on `Show.end_time`, which can wrap past midnight for very late shows with no day-rollover marker — could misjudge completion for such shows. Not hit by current sample data.

---

## Data Migration Patches (`v1_0`)

1. **recalculate_show_seat_counts** — recomputes `booked_seats`/`available_seats` on every Show from actual Confirmed bookings.
2. **set_movie_slugs** — backfills `slug` for any Movie left NULL/empty.
3. **populate_booking_source** — sets `booking_source = "Counter"` for bookings predating that custom field.

All three are idempotent and registered under `[post_model_sync]` in `patches.txt`.

### Running

```bash
bench --site cinema.localhost migrate
```

### Verifying

```python
import frappe

shows = frappe.get_all("Show", fields=["name", "total_seats", "booked_seats", "available_seats"])
assert all(s.booked_seats + s.available_seats == s.total_seats for s in shows)

assert not frappe.get_all("Movie", filters=[["slug", "in", ["", None]]])
assert not frappe.get_all("Ticket Booking", filters=[["booking_source", "in", ["", None]]])

print("All migration patches verified.")
```

---

## Report: Box Office Collection Report

Script Report at Movie level: Total Shows, Total Bookings, Total Seats Sold, Total Revenue, Avg Occupancy %, Avg Ticket Price. Filters: Theater, Date Range, Genre, Language. Bar chart (top 10 by revenue) and pie chart (revenue by screen type). Revenue is summed from `Booked Seat.seat_price`, not `total_amount` — see the known inconsistency noted above.

---

## Tests

9 integration tests in `test_ticket_booking.py`, covering seat-count decrement on submit, duplicate-seat rejection, cancelled-show rejection, max-seats enforcement, tiered refund calculation, show-overlap validation, and cancel-restores-seats.

```bash
bench --site cinema.localhost run-tests --app movietickets
```

---

## Bonus Features

- **Interactive seat map** — click-to-select grid in the booking dialog (green/red/yellow).
- **QR code tickets** — generated on booking confirmation, attached to the record, embedded in the confirmation email.
- **Box Office Dashboard** — Desk page with 4 charts: today's occupancy by theater, 30-day revenue trend, bookings by time slot, top 5 movies by booking count.
- **Movie Ticket print format** — dark cinema-themed Jinja print format with poster, QR code, and full booking detail.
- **Bulk show creator** — dialog + background job (`frappe.enqueue`) to create shows across multiple screens/dates/times in one action, respecting existing conflict validation.

---

## Known Gaps & Follow-Ups

- `Ticket Booking.total_amount` doesn't reflect per-seat `seat_price` overrides (see above) — candidate fix, touches both the controller and the client script.
- No portal page exists yet for actually creating a booking from the public "Book Now" flow (viewing-only pages are built; the create-booking portal page is missing).
- `get_seat_availability` doesn't exclude the current booking's own already-saved seats from its "booked" query — handled client-side in the booking dialog, but arguably belongs at the API level.
- `Show.compute_end_time` and the hourly status-update job don't account for shows whose `end_time` wraps past midnight.