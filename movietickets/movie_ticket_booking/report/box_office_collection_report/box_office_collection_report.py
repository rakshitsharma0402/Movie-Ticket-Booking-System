# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_bar_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{"label": "Movie Title", "fieldname": "movie_title", "fieldtype": "Data", "width": 200},
		{"label": "Genre", "fieldname": "genre", "fieldtype": "Link", "options": "Movie Genre", "width": 110},
		{"label": "Language", "fieldname": "language", "fieldtype": "Data", "width": 100},
		{"label": "Total Shows", "fieldname": "total_shows", "fieldtype": "Int", "width": 100},
		{"label": "Total Bookings", "fieldname": "total_bookings", "fieldtype": "Int", "width": 120},
		{"label": "Total Seats Sold", "fieldname": "total_seats_sold", "fieldtype": "Int", "width": 130},
		{"label": "Total Revenue", "fieldname": "total_revenue", "fieldtype": "Currency", "width": 130},
		{"label": "Avg Occupancy %", "fieldname": "avg_occupancy_pct", "fieldtype": "Percent", "width": 130},
		{"label": "Avg Ticket Price", "fieldname": "avg_ticket_price", "fieldtype": "Currency", "width": 130},
	]


def build_conditions(filters):
	"""Shared filter conditions, applied consistently across the show-
	level subquery, the booking-level subquery, and the pie-chart query.
	theater/date_range apply to Show; genre/language apply to Movie."""
	show_conditions = ["1=1"]
	movie_conditions = ["1=1"]
	params = {}

	if filters.get("theater"):
		show_conditions.append("sh.theater = %(theater)s")
		params["theater"] = filters["theater"]

	if filters.get("from_date"):
		show_conditions.append("sh.show_date >= %(from_date)s")
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		show_conditions.append("sh.show_date <= %(to_date)s")
		params["to_date"] = filters["to_date"]

	if filters.get("genre"):
		movie_conditions.append("m.genre = %(genre)s")
		params["genre"] = filters["genre"]

	if filters.get("language"):
		movie_conditions.append("m.language = %(language)s")
		params["language"] = filters["language"]

	return " AND ".join(show_conditions), " AND ".join(movie_conditions), params


def get_data(filters):
	"""Revenue is summed from Booked Seat.seat_price (actual per-seat
	price, including premium overrides), NOT Ticket Booking.total_amount
	(which uses a flat number_of_seats * price_per_seat formula that
	ignores per-seat overrides — a known inconsistency flagged in
	MTBX-3.2/MTBX-7.1). This report is therefore MORE accurate than
	total_amount for movies with premium-priced seats, and its revenue
	figures may legitimately not match MTBX-8.5's revenue API, which
	sums total_amount instead.

	Uses two separate subqueries (show-level, booking-level) joined
	back to Movie rather than one flat multi-table join, to avoid
	fan-out inflating seat-capacity sums when a Show has multiple
	booked seats."""
	show_where, movie_where, params = build_conditions(filters)

	rows = frappe.db.sql(
		f"""
		SELECT
			m.name AS movie,
			m.title AS movie_title,
			m.genre AS genre,
			m.language AS language,
			COALESCE(show_stats.total_shows, 0) AS total_shows,
			COALESCE(show_stats.total_capacity, 0) AS total_capacity,
			COALESCE(booking_stats.total_bookings, 0) AS total_bookings,
			COALESCE(booking_stats.total_seats_sold, 0) AS total_seats_sold,
			COALESCE(booking_stats.total_revenue, 0) AS total_revenue
		FROM `tabMovie` m
		LEFT JOIN (
			SELECT sh.movie AS movie,
			       COUNT(DISTINCT sh.name) AS total_shows,
			       SUM(sh.total_seats) AS total_capacity
			FROM `tabShow` sh
			WHERE {show_where}
			GROUP BY sh.movie
		) show_stats ON show_stats.movie = m.name
		LEFT JOIN (
			SELECT sh.movie AS movie,
			       COUNT(DISTINCT tb.name) AS total_bookings,
			       COUNT(bs.name) AS total_seats_sold,
			       COALESCE(SUM(bs.seat_price), 0) AS total_revenue
			FROM `tabTicket Booking` tb
			INNER JOIN `tabShow` sh ON sh.name = tb.show
			INNER JOIN `tabBooked Seat` bs ON bs.parent = tb.name
			WHERE tb.docstatus = 1 AND tb.booking_status = 'Confirmed' AND {show_where}
			GROUP BY sh.movie
		) booking_stats ON booking_stats.movie = m.name
		WHERE {movie_where}
		ORDER BY total_revenue DESC
		""",
		params,
		as_dict=True,
	)

	for row in rows:
		row["avg_occupancy_pct"] = (
			round((row["total_seats_sold"] / row["total_capacity"]) * 100, 2)
			if row["total_capacity"]
			else 0
		)
		row["avg_ticket_price"] = (
			round(row["total_revenue"] / row["total_seats_sold"], 2) if row["total_seats_sold"] else 0
		)
		del row["total_capacity"]  # internal only, not a report column

	return rows


def get_bar_chart(data):
	"""Bar chart: top 10 movies by revenue."""
	top_10 = data[:10]
	return {
		"data": {
			"labels": [row["movie_title"] for row in top_10],
			"datasets": [{"name": "Revenue", "values": [row["total_revenue"] for row in top_10]}],
		},
		"type": "bar",
	}


@frappe.whitelist()
def get_screen_type_revenue(filters=None):
	"""Data source for the pie chart (revenue by screen type). Not part
	of execute()'s single built-in chart slot, so this is a separate
	whitelisted call, invoked from box_office_collection_report.js after
	the main report renders, to render a second chart alongside it."""
	filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
	show_where, movie_where, params = build_conditions(filters)

	rows = frappe.db.sql(
		f"""
		SELECT sc.screen_type AS screen_type, COALESCE(SUM(bs.seat_price), 0) AS revenue
		FROM `tabTicket Booking` tb
		INNER JOIN `tabShow` sh ON sh.name = tb.show
		INNER JOIN `tabScreen` sc ON sc.name = sh.screen
		INNER JOIN `tabBooked Seat` bs ON bs.parent = tb.name
		INNER JOIN `tabMovie` m ON m.name = sh.movie
		WHERE tb.docstatus = 1 AND tb.booking_status = 'Confirmed'
		  AND {show_where} AND {movie_where}
		GROUP BY sc.screen_type
		""",
		params,
		as_dict=True,
	)

	return {
		"labels": [row["screen_type"] for row in rows],
		"values": [row["revenue"] for row in rows],
	}