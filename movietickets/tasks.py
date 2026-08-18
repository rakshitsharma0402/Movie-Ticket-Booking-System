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


def send_daily_revenue_digest():
	"""MTBX-11.4 — cron, daily at 23:00.
	Sends an HTML summary of today's bookings/revenue/top movie to
	every user with the Cinema Manager role. 'Today' is scoped to
	booking_time (when tickets were purchased), not show_date (when
	movies screen) — an assumption; the digest is framed as "what
	happened today" for staff, distinct from MTBX-8.5's show_date-based
	revenue reporting, which serves a different purpose."""
	current_date = today()

	stats = frappe.db.sql(
		"""
		SELECT
			COUNT(*) AS total_bookings,
			COALESCE(SUM(total_amount), 0) AS total_revenue
		FROM `tabTicket Booking`
		WHERE docstatus = 1
		  AND booking_status = 'Confirmed'
		  AND DATE(booking_time) = %(today)s
		""",
		{"today": current_date},
		as_dict=True,
	)[0]

	top_movie_row = frappe.db.sql(
		"""
		SELECT movie_title, SUM(total_amount) AS revenue
		FROM `tabTicket Booking`
		WHERE docstatus = 1
		  AND booking_status = 'Confirmed'
		  AND DATE(booking_time) = %(today)s
		GROUP BY movie_title
		ORDER BY revenue DESC
		LIMIT 1
		""",
		{"today": current_date},
		as_dict=True,
	)
	top_movie = top_movie_row[0].movie_title if top_movie_row else "N/A"

	manager_emails = frappe.get_all(
		"Has Role",
		filters={"role": "Cinema Manager", "parenttype": "User"},
		pluck="parent",
	)
	manager_emails = frappe.get_all(
		"User",
		filters={"name": ["in", manager_emails], "enabled": 1},
		pluck="email",
	)

	if not manager_emails:
		return

	html_message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px;">
		<h2>Daily Revenue Digest — {current_date}</h2>
		<table style="width: 100%; border-collapse: collapse;">
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Total Bookings</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{stats.total_bookings}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Total Revenue</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">&#8377;{stats.total_revenue}</td>
			</tr>
			<tr>
				<td style="padding: 8px;"><strong>Top Movie</strong></td>
				<td style="padding: 8px;">{top_movie}</td>
			</tr>
		</table>
	</div>
	"""

	frappe.sendmail(
		recipients=manager_emails,
		subject=f"Daily Revenue Digest — {current_date}",
		message=html_message,
	)

	