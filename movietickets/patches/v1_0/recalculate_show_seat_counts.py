# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""One-time correction: recompute booked_seats/available_seats for
	every Show from actual Confirmed Ticket Booking data, rather than
	trusting whatever incremental adjustments (MTBX-4.2's
	adjust_show_seat_counts) have accumulated to. This intentionally
	does NOT reuse that live-adjustment logic — the point of this patch
	is to correct any drift that may have occurred, not to replay the
	same incremental math."""
	shows = frappe.get_all("Show", fields=["name", "total_seats"])

	for show in shows:
		booked = (
			frappe.db.sql(
				"""
				SELECT COALESCE(SUM(number_of_seats), 0) AS total
				FROM `tabTicket Booking`
				WHERE show = %(show)s
				  AND docstatus = 1
				  AND booking_status = 'Confirmed'
				""",
				{"show": show.name},
				as_dict=True,
			)[0].total
			or 0
		)

		available = (show.total_seats or 0) - booked

		frappe.db.set_value(
			"Show",
			show.name,
			{"booked_seats": booked, "available_seats": available},
			update_modified=False,
		)

	frappe.db.commit()

    