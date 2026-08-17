# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Theater(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.SmallText
		city: DF.Data
		is_active: DF.Check
		phone: DF.Data | None
		theater_name: DF.Data
		total_screens: DF.Int
	# end: auto-generated types

	_DOCTYPE_NAME = "Theater"

	def update_total_screens(self):
		"""Recalculate total_screens from linked Screen records.
		Called by Screen's controller (see MTBX-1.4) on insert/update/
		delete of a Screen linked to this theater — not triggered from
		here, since Theater has no visibility into Screen changes on
		its own."""
		count = frappe.db.count("Screen", {"theater": self.name})
		self.db_set("total_screens", count, update_modified=False)