# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_to_date, now_datetime, nowtime, today


def expire_stale_bookings():
	"""MTBX-11.1 — cron, every 5 minutes.
	Finds Pending/Unpaid Ticket Bookings older than
	Booking Configuration.booking_expiry_minutes, marks them Expired,
	and releases their seats back onto the Show. Only ever touches
	draft (docstatus=0) bookings, since Pending only exists pre-submit
	— db_set is safe here, no cancel/docstatus semantics involved."""
	config = frappe.get_cached_doc("Booking Configuration")

	if not config.enable_auto_expiry:
		return

	cutoff = add_to_date(now_datetime(), minutes=-config.booking_expiry_minutes)

	stale_bookings = frappe.get_all(
		"Ticket Booking",
		filters={
			"booking_status": "Pending",
			"payment_status": "Unpaid",
			"booking_time": ["<", cutoff],
		},
		fields=["name", "show", "number_of_seats"],
	)

	for booking in stale_bookings:
		frappe.db.set_value(
			"Ticket Booking", booking.name, "booking_status", "Expired", update_modified=False
		)

		show = frappe.get_doc("Show", booking.show)
		show.db_set(
			"booked_seats", (show.booked_seats or 0) - booking.number_of_seats, update_modified=False
		)
		show.db_set(
			"available_seats",
			(show.available_seats or 0) + booking.number_of_seats,
			update_modified=False,
		)

	if stale_bookings:
		frappe.db.commit()


def update_movie_status():
	"""MTBX-11.2 — daily.
	Recalculates movie_status for every Movie by reusing the existing
	Movie.compute_movie_status() controller method (MTBX-1.2), so this
	job and the Movie doctype's own logic never drift apart. This is
	the fix for the staleness gap flagged back in MTBX-1.2: without
	this job, movie_status only ever updated when someone happened to
	resave a Movie record."""
	movie_names = frappe.get_all("Movie", pluck="name")

	for movie_name in movie_names:
		movie = frappe.get_doc("Movie", movie_name)
		old_status = movie.movie_status
		movie.compute_movie_status()

		if movie.movie_status != old_status:
			frappe.db.set_value(
				"Movie", movie_name, "movie_status", movie.movie_status, update_modified=False
			)

	frappe.db.commit()


def update_show_status():
	"""MTBX-11.3 — hourly.
	Transitions Show.show_status via direct bulk SQL (not per-document
	Python, for efficiency at scale):
	  Scheduled -> Now Playing: today's shows where start_time has
	    passed but end_time hasn't.
	  Scheduled/Now Playing -> Completed: end_time has passed today,
	    OR the show's date is entirely in the past.
	Cancelled shows are never touched (excluded implicitly since the
	WHERE clauses only match Scheduled/Now Playing).

	Known limitation: shows whose end_time wraps past midnight (see
	the flag from MTBX-2's compute_end_time) will show an end_time
	that appears EARLIER than start_time with no day-rollover marker,
	which could cause this comparison to misjudge such a show as
	already-completed prematurely. None of the current sample data
	hits this case."""
	current_date = today()
	current_time = nowtime()

	frappe.db.sql(
		"""
		UPDATE `tabShow`
		SET show_status = 'Now Playing'
		WHERE show_date = %(today)s
		  AND start_time <= %(now_time)s
		  AND end_time > %(now_time)s
		  AND show_status = 'Scheduled'
		""",
		{"today": current_date, "now_time": current_time},
	)

	frappe.db.sql(
		"""
		UPDATE `tabShow`
		SET show_status = 'Completed'
		WHERE show_status IN ('Scheduled', 'Now Playing')
		  AND (
		      show_date < %(today)s
		      OR (show_date = %(today)s AND end_time <= %(now_time)s)
		  )
		""",
		{"today": current_date, "now_time": current_time},
	)

	frappe.db.commit()