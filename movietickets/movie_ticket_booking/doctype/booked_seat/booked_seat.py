# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BookedSeat(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		row_letter: DF.Data
		seat_label: DF.Data
		seat_number: DF.Int
		seat_price: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Booked Seat"

	def validate(self):
		self.set_seat_price_default()

	def set_seat_price_default(self):
		"""seat_price defaults to the parent Ticket Booking's price_per_seat
		when left blank, but can be overridden per row (e.g. for premium
		seats). Not fetch_from, since that would live-mirror and overwrite
		any manual override on every parent save."""
		if self.seat_price:
			return

		if not self.parent:
			return

		price_per_seat = frappe.db.get_value("Ticket Booking", self.parent, "price_per_seat")
		if price_per_seat:
			self.seat_price = price_per_seat