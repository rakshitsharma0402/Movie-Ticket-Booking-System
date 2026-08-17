# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BookingConfiguration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		booking_expiry_minutes: DF.Int
		booking_open_days_before: DF.Int
		enable_auto_expiry: DF.Check
		full_refund_hours: DF.Float
		max_seats_per_booking: DF.Int
		partial_refund_hours: DF.Float
		partial_refund_pct: DF.Float
	# end: auto-generated types

	_DOCTYPE_NAME = "Booking Configuration"
