# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TicketBooking(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from movietickets.movie_ticket_booking.doctype.booked_seat.booked_seat import BookedSeat

		amended_from: DF.Link | None
		booked_by: DF.Link | None
		booking_status: DF.Literal["Pending", "Confirmed", "Cancelled", "Expired"]
		booking_time: DF.Datetime | None
		cancellation_reason: DF.SmallText | None
		cancellation_time: DF.Datetime | None
		customer_email: DF.Data
		customer_name: DF.Data
		customer_phone: DF.Data
		movie_title: DF.Data | None
		naming_series: DF.Literal["BKG-.YYYY.-.#####"]
		number_of_seats: DF.Int
		payment_status: DF.Literal["Unpaid", "Paid", "Refunded"]
		price_per_seat: DF.Currency
		refund_amount: DF.Currency
		screen: DF.Data | None
		seats: DF.Table[BookedSeat]
		show: DF.Link
		show_date: DF.Date | None
		start_time: DF.Time | None
		theater: DF.Data | None
		total_amount: DF.Currency
	# end: auto-generated types

	_DOCTYPE_NAME = "Ticket Booking"