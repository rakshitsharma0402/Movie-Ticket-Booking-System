# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
import json

from movietickets.movie_ticket_booking.doctype.ticket_booking.ticket_booking import SEAT_LABEL_PATTERN

@frappe.whitelist()
def get_seat_availability(show_name):
	"""Returns a 2D seat-grid representation for a Show, for the seat-
	selection dialog on Ticket Booking (MTBX-7.1).

	Row letters are derived the same way as TicketBooking's own
	seat_label validation (MTBX-4.2): row 1 = A, row 2 = B, etc., up to
	the Screen's seat_rows count. "Booked" means a seat appears in the
	Booked Seat child table of any Ticket Booking for this Show whose
	booking_status is Pending or Confirmed — mirrors the exact filter
	used in TicketBooking.validate_seats_not_already_booked, so the
	dialog's red/green rendering always agrees with what create_booking
	will actually accept or reject.

	Returns:
		{
			"seat_rows": int,
			"seats_per_row": int,
			"seats": [
				{"seat_label": "A-1", "row_letter": "A", "seat_number": 1, "status": "available"},
				{"seat_label": "A-2", "row_letter": "A", "seat_number": 2, "status": "booked"},
				...
			]
		}
	"""
	if not show_name:
		frappe.throw("show_name is required.")

	show = frappe.db.get_value("Show", show_name, ["screen"], as_dict=True)
	if not show:
		frappe.throw(f"Show '{show_name}' not found.")

	seat_rows, seats_per_row = frappe.db.get_value(
		"Screen", show.screen, ["seat_rows", "seats_per_row"]
	)

	if seat_rows > 26:
		frappe.throw(
			f"Screen has {seat_rows} rows — seat labeling only supports up to 26 (A-Z).",
			title="Unsupported Screen Configuration",
		)

	booked_labels = set(
		frappe.db.sql(
			"""
			SELECT bs.seat_label
			FROM `tabBooked Seat` bs
			INNER JOIN `tabTicket Booking` tb ON tb.name = bs.parent
			WHERE tb.show = %(show_name)s
			  AND tb.booking_status IN ('Pending', 'Confirmed')
			""",
			{"show_name": show_name},
			pluck="seat_label",
		)
	)

	seats = []
	for row_index in range(seat_rows):
		row_letter = chr(ord("A") + row_index)
		for seat_number in range(1, seats_per_row + 1):
			seat_label = f"{row_letter}-{seat_number}"
			seats.append(
				{
					"seat_label": seat_label,
					"row_letter": row_letter,
					"seat_number": seat_number,
					"status": "booked" if seat_label in booked_labels else "available",
				}
			)

	return {
		"seat_rows": seat_rows,
		"seats_per_row": seats_per_row,
		"seats": seats,
	}


@frappe.whitelist(allow_guest=False)
def create_booking(show, customer_name, customer_email, customer_phone, seats):
	"""Creates a Ticket Booking with race-condition-safe seat re-validation.

	seats: list of seat_label strings (e.g. ["A-5", "A-6"]), or a JSON-
	encoded string of the same.

	Locks the Show document (via Document.lock()/.unlock(), Frappe's
	Redis-backed document lock — frappe.lock_doc is not available in this
	Frappe version) for the duration of booking creation, then delegates
	re-validation to TicketBooking.validate() (MTBX-4.2) via
	booking.insert() — that method already re-checks show status, per-seat
	availability, duplicate seats, seat count range, and seat_label
	bounds. The lock is the only new ingredient this endpoint adds.

	Returns:
		{"success": True, "booking_name": "BKG-2026-00001",
		 "total_amount": 1350, "message": "Booking created. Complete
		 payment within 15 minutes."}
	"""
	if isinstance(seats, str):
		seats = json.loads(seats)

	if not seats:
		frappe.throw("At least one seat must be selected.")

	seat_rows = []
	for seat_label in seats:
		match = SEAT_LABEL_PATTERN.match(seat_label)
		if not match:
			frappe.throw(
				f"Seat Label '{seat_label}' is not in the required format "
				f"'ROW-NUMBER' (e.g. 'A-12')."
			)
		row_letter, seat_number = match.group(1), int(match.group(2))
		seat_rows.append(
			{"seat_label": seat_label, "row_letter": row_letter, "seat_number": seat_number}
		)

	show_doc = frappe.get_doc("Show", show)

	try:
		show_doc.lock()
	except Exception:
		frappe.log_error(frappe.get_traceback(), "create_booking: lock failed")
		frappe.throw("Could not acquire a lock on this show. Please try again in a moment.")

	try:
		booking = frappe.get_doc(
			{
				"doctype": "Ticket Booking",
				"naming_series": "BKG-.YYYY.-.#####",
				"show": show,
				"customer_name": customer_name,
				"customer_email": customer_email,
				"customer_phone": customer_phone,
				"seats": seat_rows,
			}
		)
		booking.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"booking_name": booking.name,
			"total_amount": booking.total_amount,
			"message": "Booking created. Complete payment within 15 minutes.",
		}

	except frappe.ValidationError:
		frappe.db.rollback()
		raise

	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "create_booking failed")
		frappe.throw("An unexpected error occurred while creating the booking. Please try again.")

	finally:
		show_doc.unlock()


@frappe.whitelist(allow_guest=True)
def get_shows_for_movie(movie, city=None, date=None):
	"""Returns upcoming Shows for a given Movie, for the public portal.
	Guest-accessible — no session required.

	'Upcoming' means show_date >= today and show_status in
	(Scheduled, Now Playing) — Cancelled/Completed shows are excluded.
	This is an interpretation, not explicitly defined in the spec; flag
	if same-day-but-already-started shows should also be excluded.

	city filters by the linked Theater's actual city field (a proper
	join), not a substring match against Show.theater's denormalized
	"<theater_name> - <city>" string, since that would be fragile.

	date, if given, filters to that exact show_date instead of the
	default "today onward" range.

	movie is expected to be the Movie's docname (e.g. "MOV-00001"), not
	its title — consistent with how movie is referenced elsewhere in
	the schema (Show.movie is a Link).

	Returns a list of dicts:
		[{"show_name": "SHW-2026-00001", "theater": "PVR IMAX - Ahmedabad",
		  "screen": "PVR IMAX-Screen 1", "screen_type": "IMAX",
		  "show_date": "2026-04-18", "start_time": "10:00:00",
		  "ticket_price": 450.0, "available_seats": 240}, ...]
	"""
	if not movie:
		frappe.throw("movie is required.")

	conditions = ["sh.movie = %(movie)s", "sh.show_status IN ('Scheduled', 'Now Playing')"]
	params = {"movie": movie}

	if date:
		conditions.append("sh.show_date = %(date)s")
		params["date"] = date
	else:
		conditions.append("sh.show_date >= %(today)s")
		params["today"] = frappe.utils.today()

	if city:
		conditions.append("th.city = %(city)s")
		params["city"] = city

	where_clause = " AND ".join(conditions)

	shows = frappe.db.sql(
		f"""
		SELECT
			sh.name AS show_name,
			sh.theater AS theater,
			sh.screen AS screen,
			sc.screen_type AS screen_type,
			sh.show_date AS show_date,
			sh.start_time AS start_time,
			sh.ticket_price AS ticket_price,
			sh.available_seats AS available_seats
		FROM `tabShow` sh
		INNER JOIN `tabScreen` sc ON sc.name = sh.screen
		INNER JOIN `tabTheater` th ON th.name = sh.theater
		WHERE {where_clause}
		ORDER BY sh.show_date ASC, sh.start_time ASC
		""",
		params,
		as_dict=True,
	)

	return shows


@frappe.whitelist()
def send_booking_confirmation(booking_name):
	"""Sends a formatted HTML confirmation email to the customer for a
	given Ticket Booking. Requires an authenticated session
	(allow_guest defaults to False).

	Pulls movie/theater/screen/show_date/start_time directly from the
	booking's own fetched fields (set via fetch_from in MTBX-3.1), and
	seat labels from the booking's Seats child table. Queues the email
	via frappe.sendmail() — actual delivery depends on an outgoing email
	account being configured on the site; a successful call here means
	the email was queued, not necessarily delivered.

	Returns:
		{"success": True, "message": "Confirmation email sent to
		 <email>."}
	"""
	if not booking_name:
		frappe.throw("booking_name is required.")

	booking = frappe.get_doc("Ticket Booking", booking_name)

	seat_labels = ", ".join(row.seat_label for row in booking.seats)

	html_message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
		<h2 style="color: #1a1a1a;">Booking Confirmed 🎬</h2>
		<p>Hi {frappe.utils.escape_html(booking.customer_name)},</p>
		<p>Your ticket booking is confirmed. Here are your details:</p>
		<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Booking ID</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{booking.name}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Movie</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{frappe.utils.escape_html(booking.movie_title or "")}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Theater</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{frappe.utils.escape_html(booking.theater or "")}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Screen</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{frappe.utils.escape_html(booking.screen or "")}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Show Time</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{booking.show_date} at {booking.start_time}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Seats</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{seat_labels}</td>
			</tr>
			<tr>
				<td style="padding: 8px;"><strong>Total Amount</strong></td>
				<td style="padding: 8px;">₹{booking.total_amount}</td>
			</tr>
		</table>
		<p style="color: #666; font-size: 13px;">Please arrive at least 15 minutes before showtime.</p>
	</div>
	"""

	frappe.sendmail(
		recipients=[booking.customer_email],
		subject=f"Booking Confirmed — {booking.movie_title} ({booking.name})",
		message=html_message,
	)

	return {
		"success": True,
		"message": f"Confirmation email sent to {booking.customer_email}.",
	}


@frappe.whitelist()
def get_revenue_summary(theater=None, from_date=None, to_date=None):
	"""Aggregate revenue/occupancy report, optionally filtered by theater
	and/or show date range. Requires an authenticated session.

	Only Ticket Bookings with docstatus=1 and booking_status='Confirmed'
	count toward totals — Pending bookings haven't been paid for, and
	Cancelled/Expired ones represent no revenue. This scope is an
	assumption; the spec doesn't state it explicitly.

	Date filters apply to show_date (when the movie screened), not
	booking_time (when the ticket was purchased) — also an assumption.

	avg_occupancy_pct is computed at the Show level: total seats sold
	(from confirmed bookings) divided by total seat capacity across all
	Shows matching the same theater/date filters, regardless of whether
	a given Show had any bookings at all.

	Returns:
		{"total_bookings": 42, "total_revenue": 18900.0,
		 "total_seats_sold": 126, "avg_occupancy_pct": 34.5,
		 "top_movie": "Inception"}
	"""
	booking_conditions = ["tb.docstatus = 1", "tb.booking_status = 'Confirmed'"]
	show_conditions = ["sh.show_status IN ('Scheduled', 'Now Playing', 'Completed')"]
	params = {}

	if theater:
		booking_conditions.append("tb.theater = %(theater)s")
		show_conditions.append("sh.theater = %(theater)s")
		params["theater"] = theater

	if from_date:
		booking_conditions.append("tb.show_date >= %(from_date)s")
		show_conditions.append("sh.show_date >= %(from_date)s")
		params["from_date"] = from_date

	if to_date:
		booking_conditions.append("tb.show_date <= %(to_date)s")
		show_conditions.append("sh.show_date <= %(to_date)s")
		params["to_date"] = to_date

	booking_where = " AND ".join(booking_conditions)
	show_where = " AND ".join(show_conditions)

	booking_stats = frappe.db.sql(
		f"""
		SELECT
			COUNT(*) AS total_bookings,
			COALESCE(SUM(tb.total_amount), 0) AS total_revenue,
			COALESCE(SUM(tb.number_of_seats), 0) AS total_seats_sold
		FROM `tabTicket Booking` tb
		WHERE {booking_where}
		""",
		params,
		as_dict=True,
	)[0]

	top_movie_row = frappe.db.sql(
		f"""
		SELECT tb.movie_title AS movie_title, SUM(tb.total_amount) AS revenue
		FROM `tabTicket Booking` tb
		WHERE {booking_where}
		GROUP BY tb.movie_title
		ORDER BY revenue DESC
		LIMIT 1
		""",
		params,
		as_dict=True,
	)
	top_movie = top_movie_row[0].movie_title if top_movie_row else None

	total_capacity_row = frappe.db.sql(
		f"""
		SELECT COALESCE(SUM(sh.total_seats), 0) AS total_capacity
		FROM `tabShow` sh
		WHERE {show_where}
		""",
		params,
		as_dict=True,
	)[0]

	total_capacity = total_capacity_row.total_capacity or 0
	avg_occupancy_pct = (
		round((booking_stats.total_seats_sold / total_capacity) * 100, 2)
		if total_capacity > 0
		else 0
	)

	return {
		"total_bookings": booking_stats.total_bookings,
		"total_revenue": booking_stats.total_revenue,
		"total_seats_sold": booking_stats.total_seats_sold,
		"avg_occupancy_pct": avg_occupancy_pct,
		"top_movie": top_movie,
	}


@frappe.whitelist()
def send_booking_confirmation(booking_name):
	"""Sends a formatted HTML confirmation email to the customer for a
	given Ticket Booking. Requires an authenticated session
	(allow_guest defaults to False).

	As of MTBX-17, also generates (if not already present) and embeds
	a QR code encoding the booking's details, via
	TicketBooking.get_or_create_qr_code() — reused here rather than
	duplicated, so both the on_submit doc_event (MTBX-12.1) and the
	manual "Send Booking Confirmation" button (MTBX-7.1) automatically
	pick up the QR without separate wiring.

	Returns:
		{"success": True, "message": "Confirmation email sent to
		 <email>."}
	"""
	if not booking_name:
		frappe.throw("booking_name is required.")

	booking = frappe.get_doc("Ticket Booking", booking_name)

	seat_labels = ", ".join(row.seat_label for row in booking.seats)
	qr_file_url = booking.get_or_create_qr_code()

	html_message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
		<h2 style="color: #1a1a1a;">Booking Confirmed 🎬</h2>
		<p>Hi {frappe.utils.escape_html(booking.customer_name)},</p>
		<p>Your ticket booking is confirmed. Here are your details:</p>
		<table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Booking ID</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{booking.name}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Movie</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{frappe.utils.escape_html(booking.movie_title or "")}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Theater</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{frappe.utils.escape_html(booking.theater or "")}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Screen</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{frappe.utils.escape_html(booking.screen or "")}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Show Time</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{booking.show_date} at {booking.start_time}</td>
			</tr>
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Seats</strong></td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{seat_labels}</td>
			</tr>
			<tr>
				<td style="padding: 8px;"><strong>Total Amount</strong></td>
				<td style="padding: 8px;">₹{booking.total_amount}</td>
			</tr>
		</table>
		<div style="text-align: center; margin: 20px 0;">
			<img src="cid:booking_qr" alt="Booking QR Code" style="width:180px;height:180px;">
			<p style="color: #666; font-size: 12px;">Show this code at the counter.</p>
		</div>
		<p style="color: #666; font-size: 13px;">Please arrive at least 15 minutes before showtime.</p>
	</div>
	"""

	qr_file_doc = frappe.db.get_value("File", {"file_url": qr_file_url}, ["name"], as_dict=True)
	qr_file_content = frappe.get_doc("File", qr_file_doc.name).get_content()

	frappe.sendmail(
		recipients=[booking.customer_email],
		subject=f"Booking Confirmed — {booking.movie_title} ({booking.name})",
		message=html_message,
		attachments=[
			{
				"fname": f"qr_{booking.name}.png",
				"fcontent": qr_file_content,
			}
		],
		inline_images=[{"filename": f"qr_{booking.name}.png", "cid": "booking_qr", "content": qr_file_content}],
	)

	return {
		"success": True,
		"message": f"Confirmation email sent to {booking.customer_email}.",
	}


@frappe.whitelist()
def get_todays_occupancy_by_theater():
	"""Bar chart data: today's occupancy % per theater, computed the
	same way as MTBX-13 (booked seats from Confirmed bookings / total
	Show capacity for today), grouped by theater."""
	rows = frappe.db.sql(
		"""
		SELECT
			sh.theater AS theater,
			COALESCE(SUM(sh.total_seats), 0) AS total_capacity,
			COALESCE(SUM(sh.booked_seats), 0) AS total_booked
		FROM `tabShow` sh
		WHERE sh.show_date = %(today)s
		GROUP BY sh.theater
		ORDER BY sh.theater
		""",
		{"today": frappe.utils.today()},
		as_dict=True,
	)

	labels = []
	values = []
	for row in rows:
		occupancy = round((row.total_booked / row.total_capacity) * 100, 2) if row.total_capacity else 0
		labels.append(row.theater)
		values.append(occupancy)

	return {"labels": labels, "values": values}


@frappe.whitelist()
def get_revenue_trend_30_days():
	"""Line chart data: daily revenue for the last 30 days, summed from
	Booked Seat.seat_price (not Ticket Booking.total_amount) — same
	reasoning as MTBX-13, since total_amount ignores per-seat premium
	overrides."""
	from_date = frappe.utils.add_days(frappe.utils.today(), -29)

	rows = frappe.db.sql(
		"""
		SELECT tb.show_date AS show_date, COALESCE(SUM(bs.seat_price), 0) AS revenue
		FROM `tabTicket Booking` tb
		INNER JOIN `tabBooked Seat` bs ON bs.parent = tb.name
		WHERE tb.docstatus = 1
		  AND tb.booking_status = 'Confirmed'
		  AND tb.show_date >= %(from_date)s
		GROUP BY tb.show_date
		ORDER BY tb.show_date
		""",
		{"from_date": from_date},
		as_dict=True,
	)

	revenue_by_date = {str(row.show_date): row.revenue for row in rows}

	labels = []
	values = []
	current = frappe.utils.getdate(from_date)
	today_date = frappe.utils.getdate()
	while current <= today_date:
		labels.append(str(current))
		values.append(revenue_by_date.get(str(current), 0))
		current = frappe.utils.add_days(current, 1)

	return {"labels": labels, "values": values}


@frappe.whitelist()
def get_bookings_by_time_slot():
	"""Histogram data: bookings bucketed by show start_time into four
	slots. Bucket boundaries are not spec-defined — assumption:
	Morning 6-12, Afternoon 12-17, Evening 17-21, Night 21-6."""
	rows = frappe.db.sql(
		"""
		SELECT tb.start_time AS start_time
		FROM `tabTicket Booking` tb
		WHERE tb.docstatus = 1 AND tb.booking_status = 'Confirmed'
		"""
	)

	buckets = {"Morning (6-12)": 0, "Afternoon (12-17)": 0, "Evening (17-21)": 0, "Night (21-6)": 0}

	for (start_time,) in rows:
		hour = start_time.seconds // 3600 if hasattr(start_time, "seconds") else int(str(start_time).split(":")[0])
		if 6 <= hour < 12:
			buckets["Morning (6-12)"] += 1
		elif 12 <= hour < 17:
			buckets["Afternoon (12-17)"] += 1
		elif 17 <= hour < 21:
			buckets["Evening (17-21)"] += 1
		else:
			buckets["Night (21-6)"] += 1

	return {"labels": list(buckets.keys()), "values": list(buckets.values())}


@frappe.whitelist()
def get_top_5_movies_by_bookings():
	"""Donut chart data: top 5 movies by booking COUNT (not revenue —
	distinct from MTBX-13's bar chart, which ranks by revenue)."""
	rows = frappe.db.sql(
		"""
		SELECT movie_title, COUNT(*) AS booking_count
		FROM `tabTicket Booking`
		WHERE docstatus = 1 AND booking_status = 'Confirmed'
		GROUP BY movie_title
		ORDER BY booking_count DESC
		LIMIT 5
		""",
		as_dict=True,
	)

	return {
		"labels": [row.movie_title for row in rows],
		"values": [row.booking_count for row in rows],
	}

