# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import get_time, getdate


class Show(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		available_seats: DF.Int
		booked_seats: DF.Int
		end_time: DF.Time | None
		movie: DF.Link
		movie_title: DF.Data | None
		naming_series: DF.Literal["SHW-.YYYY.-.#####"]
		screen: DF.Link
		show_date: DF.Date
		show_status: DF.Literal["Scheduled", "Now Playing", "Completed", "Cancelled"]
		start_time: DF.Time
		theater: DF.Link
		ticket_price: DF.Currency
		total_seats: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Show"

	def before_insert(self):
		self.compute_end_time()
		self.set_ticket_price_default()
		self.set_initial_seat_counts()

	def validate(self):
		self.ensure_ticket_price_present()
		self.validate_show_date_not_past()
		self.validate_movie_not_ended()
		self.validate_no_overlap()

	def on_update(self):
		self.cascade_cancellation_if_cancelled()

	def compute_end_time(self):
		"""end_time = start_time + movie.duration_minutes.
		Per MTBX-4.1 spec, this now runs only in before_insert — editing
		start_time on an existing Show will NOT recompute end_time.
		Previously this ran in validate() on every save; narrowed here
		to match spec. Flag as a follow-up if live recompute is wanted."""
		if not self.movie or not self.start_time:
			return

		duration_minutes = frappe.db.get_value("Movie", self.movie, "duration_minutes")
		if not duration_minutes:
			return

		start = get_time(self.start_time)
		start_dt = datetime.combine(datetime.today(), start)
		end_dt = start_dt + timedelta(minutes=duration_minutes)

		self.end_time = end_dt.time()

	def set_ticket_price_default(self):
		"""ticket_price defaults from Screen.base_price if not explicitly
		provided, at creation only (before_insert per spec). The separate
		'must not be empty' guard remains in validate() so edits that
		clear the field later are still caught."""
		if not self.ticket_price and self.screen:
			base_price = frappe.db.get_value("Screen", self.screen, "base_price")
			if base_price:
				self.ticket_price = base_price

	def ensure_ticket_price_present(self):
		"""Runs on every save (not just insert). ticket_price is not
		client-side Mandatory — see earlier fix — so this is the actual
		enforcement that the field can never end up empty."""
		if not self.ticket_price:
			frappe.throw(
				"Ticket Price is required and could not be defaulted from the "
				"Screen's base price. Please enter it manually.",
				title="Ticket Price Required",
			)

	def set_initial_seat_counts(self):
		"""available_seats = screen.total_seats at creation time only.
		total_seats itself is fetch_from screen.total_seats and populates
		on its own — no need to set it manually here."""
		self.booked_seats = 0
		if self.total_seats:
			self.available_seats = self.total_seats

	def validate_show_date_not_past(self):
		if not self.show_date:
			return
		if getdate(self.show_date) < getdate():
			frappe.throw(
				"Show Date cannot be in the past.",
				title="Invalid Show Date",
			)

	def validate_movie_not_ended(self):
		if not self.movie:
			return
		movie_status = frappe.db.get_value("Movie", self.movie, "movie_status")
		if movie_status == "Ended":
			frappe.throw(
				"Cannot schedule a Show for a movie whose status is Ended.",
				title="Movie Has Ended",
			)

	def validate_no_overlap(self):
		"""No other Show on the same screen should overlap this show's
		time window (start_time to end_time) on the same show_date.
		Excludes Cancelled shows from the conflict check — assumption,
		not stated explicitly in spec."""
		if not (self.screen and self.show_date and self.start_time and self.end_time):
			return

		conflicts = frappe.db.sql(
			"""
			SELECT name, start_time, end_time
			FROM `tabShow`
			WHERE screen = %(screen)s
			  AND show_date = %(show_date)s
			  AND name != %(name)s
			  AND show_status != 'Cancelled'
			  AND start_time < %(new_end_time)s
			  AND end_time > %(new_start_time)s
			""",
			{
				"screen": self.screen,
				"show_date": self.show_date,
				"name": self.name or "",
				"new_start_time": self.start_time,
				"new_end_time": self.end_time,
			},
			as_dict=True,
		)

		if conflicts:
			existing = conflicts[0]
			frappe.throw(
				f"Screen {self.screen} already has a show scheduled from "
				f"{existing.start_time} to {existing.end_time} on {self.show_date}.",
				title="Show Time Conflict",
			)

	def cascade_cancellation_if_cancelled(self):
		"""ORGANIZATION-INITIATED cancellation path. When a staff member
		sets show_status to Cancelled (the theater is pulling the show,
		not the customer choosing to cancel their seats), every
		Pending/Confirmed Ticket Booking for this Show is auto-cancelled
		with a FLAT 100% refund — customers aren't penalized for a
		decision that wasn't theirs. This is deliberately a separate,
		simpler code path from TicketBooking.on_cancel() (MTBX-4.2), which
		handles the customer-initiated path and applies the tiered refund
		schedule instead. Uses direct db-level field updates rather than
		formal .cancel(), so docstatus is left untouched — only
		booking_status and related fields change.
		booking_status -> Cancelled, cancellation_reason -> 'Show Cancelled', refund_amount
		-> total_amount (100%), payment_status -> Refunded."""

		if not self.has_value_changed("show_status") or self.show_status != "Cancelled":
			return

		bookings = frappe.get_all(
			"Ticket Booking",
			filters={"show": self.name, "booking_status": ["in", ["Pending", "Confirmed"]]},
			pluck="name",
		)

		for booking_name in bookings:
			total_amount = frappe.db.get_value("Ticket Booking", booking_name, "total_amount") or 0
			frappe.db.set_value(
				"Ticket Booking",
				booking_name,
				{
					"booking_status": "Cancelled",
					"cancellation_reason": "Show Cancelled",
					"refund_amount": total_amount,
					"payment_status": "Refunded",
					"cancellation_time": frappe.utils.now_datetime(),
				},
				update_modified=False,
			)