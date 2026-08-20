# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe

no_cache = 1


def get_context(context):
	"""Portal seat-selection and booking-creation page. Login required —
	mirrors the guest-check already used by the "Book Now" button on
	movie-shows.html. Reuses the existing get_seat_availability
	(MTBX-8.1) and create_booking (MTBX-8.2) APIs entirely — this page
	is purely a UI layer over already-tested backend logic, not new
	business logic."""
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=" + frappe.utils.quote(
			frappe.request.path + "?" + frappe.request.query_string.decode()
		)
		raise frappe.Redirect

	context.no_cache = 1

	show_name = frappe.form_dict.get("show")
	if not show_name:
		frappe.throw("Show not specified.", frappe.DoesNotExistError)

	show = frappe.db.get_value(
		"Show",
		show_name,
		["movie_title", "theater", "screen", "show_date", "start_time", "ticket_price", "show_status"],
		as_dict=True,
	)
	if not show:
		frappe.throw(f"Show '{show_name}' not found.", frappe.DoesNotExistError)

	context.show = show
	context.show_name = show_name

	user = frappe.get_doc("User", frappe.session.user)
	context.prefill_name = user.full_name or ""
	context.prefill_email = user.email or ""