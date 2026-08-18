# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe

no_cache = 1


def get_context(context):
	"""Logged-in user's own booking history. Redirects guests to /login.
	Queries filtered by booked_by = session user directly; this also
	naturally respects the has_permission restriction on Ticket Booking
	(MTBX-9) even without the explicit filter, but the filter is kept
	for clarity and to avoid relying solely on the permission layer."""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/my-bookings"
		raise frappe.Redirect

	context.no_cache = 1

	context.bookings = frappe.db.get_all(
		"Ticket Booking",
		filters={"booked_by": frappe.session.user},
		fields=[
			"name",
			"movie_title",
			"show_date",
			"start_time",
			"number_of_seats",
			"total_amount",
			"booking_status",
		],
		order_by="show_date desc, start_time desc",
	)