# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Screen(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_price: DF.Currency
		is_active: DF.Check
		screen_name: DF.Data
		screen_type: DF.Literal["Standard", "IMAX", "3D", "4DX"]
		seat_rows: DF.Int
		seats_per_row: DF.Int
		theater: DF.Link
		total_seats: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Screen"

	def autoname(self):
		"""Autoname as '<theater_name>-<screen_name>', e.g. 'PVR IMAX-Screen 1'.
		Uses the linked Theater's short theater_name, not its full docname
		(which includes a city suffix, e.g. 'PVR IMAX - Ahmedabad') — a plain
		format: autoname on the theater Link field would pull in the city
		and produce the wrong name."""
		if not self.theater or not self.screen_name:
			frappe.throw("Theater and Screen Name are required to generate a name.")

		theater_name = frappe.db.get_value("Theater", self.theater, "theater_name")
		if not theater_name:
			frappe.throw(f"Could not resolve theater_name for Theater '{self.theater}'.")

		self.name = f"{theater_name}-{self.screen_name}"

	def validate(self):
		self.validate_seat_math()

	def validate_seat_math(self):
		if self.total_seats is None or self.seat_rows is None or self.seats_per_row is None:
			return

		expected = self.seat_rows * self.seats_per_row
		if self.total_seats != expected:
			frappe.throw(
				f"Total Seats ({self.total_seats}) must equal Seat Rows × Seats Per Row "
				f"({self.seat_rows} × {self.seats_per_row} = {expected}).",
				title="Seat Count Mismatch",
			)

	def after_insert(self):
		self.sync_theater_screen_count()

	def on_update(self):
		self.sync_theater_screen_count()

	def after_delete(self):
		self.sync_theater_screen_count()

	def sync_theater_screen_count(self):
		if self.theater:
			frappe.get_doc("Theater", self.theater).update_total_screens()