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
	encoded string of the same — whitelisted methods often receive list
	arguments as JSON strings when called over HTTP rather than from the
	console, so both forms are accepted here.

	Locks the Show document for the duration of booking creation, then
	delegates the actual re-validation to TicketBooking.validate() (built
	in MTBX-4.2) via booking.insert() — that method already re-checks show
	status, per-seat availability, duplicate seats, seat count range, and
	seat_label bounds. Duplicating those checks here would just create a
	second copy to keep in sync; the lock is the only new ingredient this
	endpoint needs to add.

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

	try:
		frappe.lock_doc("Show", show)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "create_booking: lock_doc failed")
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
		# insert() runs TicketBooking.validate() — the show-status check,
		# per-seat availability check, duplicate-seat check, seat count
		# range, and seat_label bounds check are all re-run here, now
		# safely inside the Show-level lock acquired above.
		booking.insert(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"booking_name": booking.name,
			"total_amount": booking.total_amount,
			"message": "Booking created. Complete payment within 15 minutes.",
		}

	except frappe.ValidationError:
		# Expected, user-facing validation failures (seat taken, show not
		# bookable, etc.) — roll back and let the original message surface
		# to the client as-is, no need to log these as system errors.
		frappe.db.rollback()
		raise

	except Exception:
		frappe.db.rollback()
		frappe.log_error(frappe.get_traceback(), "create_booking failed")
		frappe.throw("An unexpected error occurred while creating the booking. Please try again.")

	finally:
		frappe.unlock_doc("Show", show)