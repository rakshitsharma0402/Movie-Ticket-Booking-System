# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta

import frappe
from frappe.model.document import Document
from frappe.utils import get_time


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

	def validate(self):
		self.set_ticket_price_default()
		self.compute_end_time()
		self.set_initial_seat_counts()

	def set_ticket_price_default(self):
		"""ticket_price defaults from the Screen's base_price, but only
		on a new, still-empty record — never overwrites a value the user
		already set or a value carried over from a prior save. This is
		deliberately NOT fetch_from, which would clobber overrides every
		time the screen link is touched."""
		if self.is_new() and not self.ticket_price and self.screen:
			base_price = frappe.db.get_value("Screen", self.screen, "base_price")
			if base_price:
				self.ticket_price = base_price

	def compute_end_time(self):
		"""end_time = start_time + movie.duration_minutes.
		Recomputed whenever movie or start_time is set/changed, since both
		determine the result."""
		if not self.movie or not self.start_time:
			return

		duration_minutes = frappe.db.get_value("Movie", self.movie, "duration_minutes")
		if not duration_minutes:
			return

		start = get_time(self.start_time)
		start_dt = datetime.combine(datetime.today(), start)
		end_dt = start_dt + timedelta(minutes=duration_minutes)

		self.end_time = end_dt.time()

	def set_initial_seat_counts(self):
		"""available_seats mirrors total_seats only at creation time — not
		a live fetch_from, since future booking logic (MTBX-3) will need to
		decrement available_seats independently as seats get booked."""
		if self.is_new():
			self.booked_seats = 0
			if self.total_seats:
				self.available_seats = self.total_seats