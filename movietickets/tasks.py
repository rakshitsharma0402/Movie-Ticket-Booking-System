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

