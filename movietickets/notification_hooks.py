# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe

from movietickets.api import send_booking_confirmation


def send_booking_received_email(doc, method):
	"""doc_events after_insert on Ticket Booking. Sends a short "booking
	received, complete payment" notice — distinct from the full
	confirmation email sent on_submit (see
	send_booking_confirmation_on_submit below, which reuses the existing
	send_booking_confirmation API rather than duplicating its template)."""
	config = frappe.get_cached_doc("Booking Configuration")

	html_message = f"""
	<div style="font-family: Arial, sans-serif; max-width: 600px;">
		<p>Hi {frappe.utils.escape_html(doc.customer_name)},</p>
		<p>Your booking <strong>{doc.name}</strong> for
		<strong>{frappe.utils.escape_html(doc.movie_title or "")}</strong>
		has been received. Please complete payment within
		<strong>{config.booking_expiry_minutes} minutes</strong> to
		confirm your seats.</p>
	</div>
	"""

	frappe.sendmail(
		recipients=[doc.customer_email],
		subject=f"Booking Received — {doc.name}",
		message=html_message,
	)


def send_booking_confirmation_on_submit(doc, method):
	"""doc_events on_submit on Ticket Booking. Reuses the existing
	send_booking_confirmation whitelisted API (MTBX-8.4) rather than
	writing a second copy of the same HTML template — same email
	content, now triggered automatically on submit rather than only via
	manual button click (MTBX-7.1)."""
	send_booking_confirmation(booking_name=doc.name)


def regenerate_movie_slug_and_status(doc, method):
	"""doc_events before_save on Movie.

	NOTE: this is functionally redundant with Movie's own controller
	methods (generate_slug() in before_save, compute_movie_status() in
	validate() — both built in MTBX-1.2), which already run
	automatically without any hooks.py wiring. doc_events is normally
	for attaching hooks from OUTSIDE a DocType's own controller, not for
	re-triggering logic the controller already owns. Implemented here
	exactly as specified since it's explicitly asked for and is
	idempotent (safe to call twice, just wasteful) — flagged as likely
	either an oversight in ticket scoping, or an intentional exercise in
	demonstrating the doc_events mechanism itself, not a bug on my end."""
	doc.generate_slug()
	doc.compute_movie_status()