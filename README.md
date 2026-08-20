# Movie Tickets Booking (MTBX)

A Frappe app for browsing movies, scheduling shows, and booking tickets — built end-to-end as a developer training assessment, covering DocTypes, server-side controllers, client scripts, whitelisted APIs, role-based permissions, a public web portal, scheduled jobs, hooks, a Script Report, data migration patches, unit tests, and a handful of bonus features. Subsequently hardened through a full regression pass that found and fixed 14+ real bugs before being demoed end-to-end (guest booking flow, staff booking flow, reporting, dashboard) with no known blockers.

- **Framework:** Frappe (bench app name: `movietickets`)
- **Local dev site:** `cinema.localhost`
- **Python module for DocTypes:** `movietickets/movie_ticket_booking/doctype/...`
- **Top-level app files:** `movietickets/hooks.py`, `movietickets/api.py`, `movietickets/tasks.py`

---

## Setup

```bash
bench init cinema-bench --frappe-branch version-16
bench new-site cinema.localhost
bench get-app git@github.com:rakshitsharma0402/Movie-Ticket-Booking-System.git
bench --site cinema.localhost install-app movietickets
bench use cinema.localhost
bench start
```

Visit `http://cinema.localhost:8000` and log in as Administrator.

Verified to install cleanly from a **fresh GitHub clone** with zero manual steps beyond the above — fixtures and migration patches run automatically on `install-app`/`migrate`.

### Dependencies

QR code generation requires `qrcode[pil]`, declared in `pyproject.toml`'s `[project].dependencies` and installed automatically via `bench get-app`. If installing manually:

```bash
./env/bin/pip install qrcode[pil] --break-system-packages
```

> **Note:** this app's `pyproject.toml` previously had a stray, invalid line appended after `qrcode[pil]` was added for MTBX-17, which broke `bench get-app` on every fresh clone with a `TOMLDecodeError`. Fixed — `qrcode[pil]` now lives correctly inside the `dependencies` array.

### Demo Data (optional)

To populate a fresh install with sample movies, theaters, screens, shows, bookings, and the three demo role users:

```bash
bench --site cinema.localhost execute movietickets.demo_data.run
```

Deliberately **not** shipped as fixtures — Show dates are computed relative to "today" at run-time (e.g. `today`, `today + 1`, `today + 6`), so the seed data stays meaningful no matter when the repo is cloned. Fixtures would have frozen fixed calendar dates that go stale. The script is idempotent — safe to re-run on a site that already has some or all of this data; it skips anything that already exists.

Seeds:
- 8 Movie Genres, 6 Movies (dates offset from today so status — Now Showing/Upcoming/Ended — comes out correctly regardless of when you run it)
- 4 Theaters, 8 Screens
- 7 Shows (today/upcoming, so they're actually bookable)
- 4 sample Confirmed Ticket Bookings (so reports/dashboards show real numbers immediately)
- Booking Configuration defaults
- 3 demo users — `manager@test.com` (Cinema Manager), `staff@test.com` (Box Office Staff), `customer@test.com` (Customer) — all password `Demo@1234`

### Where to go as each user

| User | Login | What to visit |
|---|---|---|
| **Guest** (not logged in) | — | `/now-showing` → browse movies → click a card → `/movie-shows?movie=MOV-XXXXX` → click Book Now → redirected to `/login` |
| **Customer** | `customer@test.com` / `Demo@1234` | `/now-showing`, `/movie-shows?movie=MOV-XXXXX` → Book Now → `/book-seats?show=SHW-XXXXX` (pick seats, fill details, confirm) → redirected to `/my-bookings` to see the new booking. **No Desk access** — `/app/*` correctly shows "Not Permitted." |
| **Box Office Staff** | `staff@test.com` / `Demo@1234` | `/app/ticket-booking/new` → select a Show → Select Seats → fill customer details → Submit → Send Booking Confirmation → Print (renders the QR-code ticket). Read-only on `/app/movie`, `/app/theater`, `/app/screen`, `/app/show` — create/edit attempts are blocked. |
| **Cinema Manager** | `manager@test.com` / `Demo@1234` | Full access everywhere: `/app/movie`, `/app/theater`, `/app/screen`, `/app/show`, `/app/ticket-booking`, `/app/booking-configuration`, `/app/box-office-dashboard`, and the Box Office Collection Report (`/app/query-report/Box Office Collection Report`). Can cancel a Show and watch its bookings auto-refund at 100%. |
| **Administrator** | (your own login) | Everything above, plus Bulk Create Shows (from the Show list toolbar) and direct DocType access for setup/debugging. |

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
- **`seat_price` defaulting is computed at the parent level:** `Ticket Booking.set_default_seat_prices()`, called at the end of the parent's own `validate()`, defaults each Booked Seat row's price from `price_per_seat` when left blank. This intentionally does **not** live in `Booked Seat`'s own `validate()` — the child table validates before the parent's `fetch_from` fields are guaranteed populated, which caused a real, silent bug (seat prices staying `0`/`None` on nearly every booking) until traced and fixed during the regression pass.
- **`Ticket Booking.total_amount`** still uses a flat `number_of_seats × price_per_seat` formula and does **not** sum individual `seat_price` overrides, even though the schema supports premium per-seat pricing. The Box Office Collection Report and Dashboard deliberately sum `seat_price` directly instead, so their revenue figures may legitimately diverge from `total_amount`-based figures (e.g. `get_revenue_summary`). Flagged as a candidate fix, not yet done.

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

Dashboard chart data endpoints (`get_todays_occupancy_by_theater`, `get_revenue_trend_30_days`, `get_bookings_by_time_slot`, `get_top_5_movies_by_bookings`) and the report's `get_screen_type_revenue` also live in `api.py` / the report module respectively.

> **Type annotations are required on every whitelisted argument** in this Frappe version (`require_type_annotated_api_methods = True` in `hooks.py`) — a missing or mismatched annotation causes a silent-looking `417 FrappeTypeError` that does **not** reliably surface when testing via `frappe.call()` from a `bench console` session, only on real HTTP requests. This bit the project repeatedly during the regression pass (`get_count_with_logging`, the report's `get_screen_type_revenue`, and `create_shows_bulk`'s `screens`/`show_times` params all needed fixes). **Any new whitelisted function must be tested through an actual browser/HTTP call, not just the console, before being considered verified.**

---

## Web Portal

| Page | Access | Description |
|---|---|---|
| `/now-showing` | Guest | Card grid of Now Showing movies, genre/language filters |
| `/movie-shows?movie=MOV-XXXXX` | Guest (viewing) / Login (booking) | Shows grouped by theater and date, "Book Now" |
| `/book-seats?show=SHW-XXXXX` | Login required | **New** — self-service seat selection and booking creation, reusing `get_seat_availability`/`create_booking` |
| `/my-bookings` | Login required | Logged-in user's booking history with status badges |

> **Portal controller filenames must use underscores, not hyphens** (`now_showing.py`, `my_bookings.py`, `movie_shows.py`, `book_seats.py`), even though their paired `.html` templates use hyphens matching the route. Frappe's `TemplatePage.set_pymodule()` converts hyphens to underscores when looking for a page's Python controller — Python module names can't contain hyphens. All three original portal pages were built with hyphenated `.py` filenames and silently rendered as pure static templates with zero context (no error, just empty/broken pages) until this was traced and fixed. `book_seats.py` was built correctly from the start using this lesson.

---

## Roles & Permissions

| Role | Access |
|---|---|
| Cinema Manager | Full CRUD + submit/cancel on all DocTypes |
| Box Office Staff | Create/submit/cancel bookings; read-only on Movie/Theater/Screen/Show; read access to Print Format (required to print tickets) |
| Customer | Create bookings (own only); read-only Movie/Show; no Theater/Screen access; portal-only (no Desk access) |

Row-level restriction is intended via a `has_permission` hook on Ticket Booking (`booked_by == session user` for Customer-role users). **This hook does not reliably restrict `frappe.get_list()`/`frappe.get_doc()` access** — confirmed during the regression pass: a Customer-role user querying via console or Desk could see all bookings, not just their own. The only place this is actually enforced today is `/my-bookings`' own explicit `filters={"booked_by": frappe.session.user}` query. **A `permission_query_conditions` hook is likely needed as a companion to `has_permission` to close this gap** — flagged, not yet fixed.

Test users: `manager@test.com`, `staff@test.com`, `customer@test.com` (all password `Demo@1234` in demo seed data).

---

## Scheduled Jobs (`movietickets/tasks.py`)

| Job | Schedule | Purpose |
|---|---|---|
| `expire_stale_bookings` | Every 5 min (cron) | Expires stale Pending/Unpaid bookings, releases seats |
| `update_movie_status` | Daily | Recalculates `movie_status` for all movies |
| `update_show_status` | Hourly | Transitions shows through Now Playing → Completed |
| `send_daily_revenue_digest` | Daily at 23:00 (cron) | Emails Cinema Managers a summary of the day's bookings/revenue |

All four confirmed running correctly via manual invocation during the regression pass, including verifying `update_movie_status`/`update_show_status` correctly transition real accumulated data.

> **Known limitation:** `update_show_status` relies on `Show.end_time`, which can wrap past midnight for very late shows with no day-rollover marker — could misjudge completion for such shows. Not hit by current sample data.

---

## Hooks & Email Handling

- **`hooks.py` doc_events** wire `after_insert`/`on_submit` on Ticket Booking (customer emails) and `before_save` on Movie (redundant with the Movie controller's own logic — flagged as likely a duplicated-hooks exercise, not fixed since it's harmless/idempotent).
- **Email failures never block core actions.** `send_booking_received_email`, `send_booking_confirmation_on_submit`, and `send_daily_revenue_digest` are all wrapped in `try/except` with `frappe.clear_messages()` + `frappe.log_error()`. This was a **critical bug** found during regression testing: an unwrapped `OutgoingEmailError` (no configured outgoing Email Account, the default local-dev state) was silently blocking every Ticket Booking insert and submit, site-wide, until fixed. The one deliberately **unwrapped** call is `send_booking_confirmation` (called from the "Send Booking Confirmation" button) — a user explicitly asking to send an email should see a clear failure if it can't be sent, unlike the background hooks.
- **`override_whitelisted_methods`** demos wrapping `frappe.client.get_count` with logging (`overrides.py`) — a working example of the mechanism, documented with use cases/risks/alternatives in the module docstring.

---

## Report: Box Office Collection Report

Script Report at Movie level: Total Shows, Total Bookings, Total Seats Sold, Total Revenue, Avg Occupancy %, Avg Ticket Price. Filters: Theater, Date Range, Genre, Language. Bar chart (top 10 by revenue, built into `execute()`) and pie chart (revenue by screen type, rendered via a separate whitelisted call + client-side chart insertion, since Script Reports only support one built-in chart slot). Revenue is summed from `Booked Seat.seat_price`, not `total_amount` — see the known inconsistency noted above. Confirmed rendering correctly with real data, both charts, working filters.

---

## Dashboard: Box Office Dashboard

Desk page (`/app/box-office-dashboard`) with four charts: today's occupancy by theater (bar), 30-day revenue trend (line), bookings by time slot (bar/histogram, 4 fixed buckets: Morning/Afternoon/Evening/Night — bucket boundaries are an assumption, not spec-defined), top 5 movies by booking count (donut). Confirmed rendering with no console errors during regression testing.

---

## Tests

9 integration tests in `test_ticket_booking.py` (base class `IntegrationTestCase`, matching this Frappe version's scaffold — not the older `FrappeTestCase`), covering seat-count decrement on submit, duplicate-seat rejection, cancelled-show rejection, max-seats enforcement, tiered refund calculation, show-overlap validation, and cancel-restores-seats.

```bash
bench --site cinema.localhost run-tests --app movietickets
```

All 9 pass. Note: `bench run-tests` (without `--app`) fails in this environment due to a missing `hypothesis` package needed only by Frappe's own core test suite — always scope with `--app movietickets`.

---

## Bonus Features

- **Interactive seat map** — click-to-select grid in the booking dialog and on `/book-seats` (green/red/yellow, yellow chosen over the original blue per spec).
- **QR code tickets** — generated on booking confirmation via `TicketBooking.get_or_create_qr_code()`, attached to the record, embedded in the confirmation email. Confirmed rendering correctly, scannable, decodes to readable booking details.
- **Box Office Dashboard** — see above.
- **Movie Ticket print format** — dark cinema-themed Jinja print format with poster, QR code, and full booking detail. Requires Box Office Staff to have `Print Format` read access (see Roles & Permissions) — this was missing and blocking printing entirely until fixed during a live staff-side demo run.
- **Bulk show creator** — dialog + background job (`frappe.enqueue`) to create shows across multiple screens/dates/times in one action, respecting existing conflict validation by reusing `Show.insert()`'s normal controller path (no duplicated validation logic).

---

## Assumptions

The spec was silent on a number of details; these are the choices made, so they're explicit rather than buried in code comments:

- **"Upcoming shows"** (`get_shows_for_movie`) means `show_date >= today` and `show_status` in `Scheduled`/`Now Playing` — same-day shows whose `start_time` has already passed are still included, not filtered out.
- **`city` filtering** joins to the Theater's actual `city` field rather than substring-matching Show's denormalized `theater` string.
- **`movie` parameters** across the API expect the Movie **docname** (`MOV-00001`), not its title.
- **Revenue scope**: only `docstatus=1, booking_status='Confirmed'` bookings count as revenue anywhere in the app (reports, dashboard, digest) — Pending/Cancelled/Expired are excluded throughout.
- **Daily revenue digest "today"** is scoped to `booking_time` (when the ticket was purchased), not `show_date` (when the movie screens) — deliberately different from the Report/`get_revenue_summary`, which scope by `show_date`, since a digest for staff is framed as "what happened today," not "revenue for shows today."
- **Time-slot histogram buckets** (Morning 6–12 / Afternoon 12–17 / Evening 17–21 / Night 21–6) are arbitrary, not spec-defined.
- **Screen cancellation cascade**: an organization-cancelled Show only cascades to Pending/Confirmed bookings; Cancelled/Expired bookings are left untouched.
- **Overlap validation** excludes Cancelled shows from the conflict check — a cancelled slot doesn't block a new booking on that screen/time.
- **26-row cap**: seat labeling (A–Z) assumes no Screen ever has more than 26 rows; both `get_seat_availability` and the booking validator throw explicitly rather than silently corrupting labels past Z.
- **"Book seats via portal only"** (Customer role) is enforced by giving Customer no Desk Access at all, not by any request-origin check — a Customer with Desk access (if one were ever granted) could otherwise create bookings from the Desk too.

---

## Known Gaps & Follow-Ups

- `Ticket Booking.total_amount` doesn't reflect per-seat `seat_price` overrides — the Report/Dashboard already work around this by summing `seat_price` directly; `total_amount` itself is unfixed.
- `has_permission` on Ticket Booking doesn't actually restrict `get_list`/`get_doc` access — only `/my-bookings`' own explicit filter enforces row-level privacy today. A `permission_query_conditions` hook is the likely fix.
- `get_seat_availability` doesn't exclude the current booking's own already-saved seats from its "booked" query — handled client-side in both the Desk dialog and `/book-seats`, but arguably belongs at the API level.
- `Show.compute_end_time` and the hourly status-update job don't account for shows whose `end_time` wraps past midnight.
- No migration patch exists to correct `Theater.total_screens` drift from pre-fix Screen deletions, or to backfill `Ticket Booking`/`Booked Seat` financial fields the way `recalculate_show_seat_counts` does for Show — both classes of drift were found and manually repaired during the regression pass, but no automated patch exists for either.
- Any new whitelisted API function must be smoke-tested via a real browser/HTTP request before being trusted — console-level `frappe.call()` testing has repeatedly given false "it works" results on type-annotation issues in this Frappe version.
