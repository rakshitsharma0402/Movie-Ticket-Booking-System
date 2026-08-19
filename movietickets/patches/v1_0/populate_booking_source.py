# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Backfills booking_source = 'Counter' for existing Ticket Bookings
	created before the field existed (MTBX-6), where it's currently
	NULL/empty. New bookings going forward already default to 'Website'
	per the Custom Field's own default — this only touches pre-existing
	rows created before that default applied."""
	frappe.db.sql(
		"""
		UPDATE `tabTicket Booking`
		SET booking_source = 'Counter'
		WHERE booking_source IS NULL OR booking_source = ''
		"""
	)
	frappe.db.commit()

    