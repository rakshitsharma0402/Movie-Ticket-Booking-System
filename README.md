# Movie Tickets Booking (MTBX)

A ticket booking platform for movie theaters, built as a [Frappe](https://frappeframework.com/) app. It covers the full lifecycle of running shows and selling seats — theater and screen setup, show scheduling, seat-level booking with premium pricing, and a two-tier cancellation/refund model — all backed by Frappe's DocType and permission system.

## Why this exists

Booking systems look simple from the outside but have a surprising number of edge cases once you dig in: seats that need per-row pricing, cancellations that behave differently depending on who initiated them, and capacity numbers that have to stay in sync as screens are added or removed. This project was built to work through those problems properly rather than stub them out — including the messier parts like locking, refund thresholds, and seat-label generation.

## Features

**Theater & Screen management**
- Theaters own a set of screens, with `total_screens` kept in sync automatically as screens are added or removed
- Screen capacity drives seat map generation

**Shows & Seat Booking**
- Shows are scheduled against a specific screen and time slot
- Seat maps are generated with row/column labels (A, B, C… capped at 26 rows)
- Per-seat price overrides for premium seating, tracked in a Booked Seat child table

**Bookings & Refunds**
- Two distinct cancellation paths, because "who cancelled" changes the rules:
  - **Organization-initiated** (a show gets cancelled outright): flat 100% refund, applied directly without touching document status
  - **Customer-initiated** (a single booking gets cancelled): tiered refund based on how close to showtime the cancellation happens, driven by Frappe's document cancellation lifecycle
- Refund thresholds are configurable via a central Booking Configuration doctype

**Permissions & Access**
- Role-based access control so customers only see and manage their own bookings
- Whitelisted APIs for the booking flow, separate from the internal controller logic

**Customer Portal**
- Web portal pages for browsing shows and booking seats
- *(In progress — see Roadmap below)*

## Tech Stack

- **Framework:** Frappe (Python + JS)
- **Database:** MariaDB
- **Caching/Locking:** Redis, via Frappe's document locking API
- **Frontend:** Frappe's client-side framework + portal pages

## App Structure

```
movietickets/
├── api.py                          # Whitelisted endpoints for booking flow
├── hooks.py                        # App hooks (scheduled jobs, doc events)
└── movie_ticket_booking/
    └── doctype/
        ├── theater/
        ├── screen/
        ├── show/
        ├── ticket_booking/
        ├── booked_seat/
        └── booking_configuration/
```

## Setup

```bash
# Get the app
bench get-app movietickets <repo-url>

# Create or use an existing site
bench new-site cinema.localhost

# Install the app
bench --site cinema.localhost install-app movietickets

# Start the dev server
bench start
```

## Roadmap

Not everything made it in yet — here's what's still open:

- **My Bookings portal page** — pending a decision on how seat availability should be surfaced (this is blocking the last portal piece)
- **Scheduled jobs** — automated cleanup/reminders via `hooks.py`
- **Script Report** — reporting on bookings/occupancy
- **Data migration patches**
- **Automated test suite**
- **Bonus enhancements** — lower priority, not yet started

## Notable design decisions

- Seat pricing (`ticket_price`, `available_seats`) is computed once on creation rather than recalculated on every save, to avoid surprising existing bookings when show details change later.
- Refund threshold lookups use a cached document read rather than a fresh query on every booking save.
- There's a known inconsistency worth resolving before this goes further: total booking amount is currently calculated as a flat `seats × price`, which doesn't account for per-seat premium pricing overrides. Documenting it here so it doesn't get lost.

## License

MIT