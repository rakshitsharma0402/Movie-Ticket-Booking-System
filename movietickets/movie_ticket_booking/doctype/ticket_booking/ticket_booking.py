# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

SEAT_LABEL_PATTERN = re.compile(r"^([A-Z])-(\d+)$")

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

	def validate(self):
		self.validate_show_status()
		self.validate_no_duplicate_seats_in_booking()
		self.validate_seats_not_already_booked()
		self.validate_seat_label_format_and_bounds()
		self.calculate_totals()
		self.validate_seat_count_range()
		self.set_default_seat_prices()

	def on_submit(self):
		self.booking_status = "Confirmed"
		self.payment_status = "Paid"
		self.db_set("booking_status", "Confirmed", update_modified=False)
		self.db_set("payment_status", "Paid", update_modified=False)
		self.adjust_show_seat_counts(seats_delta=self.number_of_seats)

	def on_cancel(self):
		self.calculate_refund()
		self.db_set("booking_status", "Cancelled", update_modified=False)
		self.db_set("cancellation_time", now_datetime(), update_modified=False)
		self.adjust_show_seat_counts(seats_delta=-self.number_of_seats)

	# ---------- validate() helpers ----------

	def validate_show_status(self):
		show_status = frappe.db.get_value("Show", self.show, "show_status")
		if show_status not in ("Scheduled", "Now Playing"):
			frappe.throw(
				f"Cannot book tickets for a {show_status} show.",
				title="Show Not Bookable",
			)

	def validate_no_duplicate_seats_in_booking(self):
		seen = set()
		for row in self.seats:
			if row.seat_label in seen:
				frappe.throw(
					f"Seat {row.seat_label} is duplicated within this booking.",
					title="Duplicate Seat",
				)
			seen.add(row.seat_label)

	def validate_seats_not_already_booked(self):
		"""Checks every seat in this booking against seats already taken
		by Pending/Confirmed bookings for the same Show, excluding this
		document itself (relevant on resubmission/amendment)."""
		if not self.seats:
			return

		seat_labels = [row.seat_label for row in self.seats]

		taken = frappe.db.sql(
			"""
			SELECT bs.seat_label
			FROM `tabBooked Seat` bs
			INNER JOIN `tabTicket Booking` tb ON tb.name = bs.parent
			WHERE tb.show = %(show)s
			  AND tb.name != %(name)s
			  AND tb.booking_status IN ('Pending', 'Confirmed')
			  AND bs.seat_label IN %(seat_labels)s
			""",
			{
				"show": self.show,
				"name": self.name or "",
				"seat_labels": seat_labels,
			},
			as_dict=True,
		)

		if taken:
			frappe.throw(
				f"Seat {taken[0].seat_label} is already booked for this show.",
				title="Seat Unavailable",
			)

	def validate_seat_label_format_and_bounds(self):
		"""seat_label must match '{ROW_LETTER}-{SEAT_NUMBER}' (e.g. 'A-12'),
		agree with the row's own row_letter/seat_number fields, and fall
		within the Screen's seat_rows/seats_per_row bounds. Row letters are
		derived A, B, C... up to seat_rows (row 1 = A, row 2 = B, etc.) —
		same scheme as api.get_seat_availability (MTBX-8.1), guarded the
		same way against >26-row screens."""
		if not self.seats or not self.screen:
			return

		seat_rows, seats_per_row = frappe.db.get_value(
			"Screen", self.screen, ["seat_rows", "seats_per_row"]
		)
		if not seat_rows or not seats_per_row:
			return

		if seat_rows > 26:
			frappe.throw(
				f"Screen has {seat_rows} rows — seat labeling only supports up to 26 (A-Z).",
				title="Unsupported Screen Configuration",
			)

		valid_row_letters = {chr(ord("A") + i) for i in range(seat_rows)}

		for row in self.seats:
			match = SEAT_LABEL_PATTERN.match(row.seat_label or "")
			if not match:
				frappe.throw(
					f"Seat Label '{row.seat_label}' is not in the required "
					f"format 'ROW-NUMBER' (e.g. 'A-12').",
					title="Invalid Seat Label",
				)

			label_row, label_number = match.group(1), int(match.group(2))

			if row.row_letter != label_row or row.seat_number != label_number:
				frappe.throw(
					f"Seat Label '{row.seat_label}' does not match its own "
					f"Row Letter ('{row.row_letter}') and Seat Number "
					f"('{row.seat_number}').",
					title="Invalid Seat Label",
				)

			if label_row not in valid_row_letters:
				frappe.throw(
					f"Row '{label_row}' is out of range for this Screen "
					f"(valid rows: A–{chr(ord('A') + seat_rows - 1)}).",
					title="Seat Out of Range",
				)

			if not (1 <= label_number <= seats_per_row):
				frappe.throw(
					f"Seat number {label_number} is out of range for this "
					f"Screen (valid: 1–{seats_per_row}).",
					title="Seat Out of Range",
				)

	def calculate_totals(self):
		self.number_of_seats = len(self.seats)
		self.total_amount = (self.number_of_seats or 0) * (self.price_per_seat or 0)

	def validate_seat_count_range(self):
		max_seats = frappe.get_cached_doc("Booking Configuration").max_seats_per_booking
		if not (1 <= self.number_of_seats <= max_seats):
			frappe.throw(
				f"A booking must contain between 1 and {max_seats} seats "
				f"(got {self.number_of_seats}).",
				title="Invalid Seat Count",
			)

	def set_default_seat_prices(self):
		"""Defaults each Booked Seat row's seat_price to this booking's
		price_per_seat when left blank, preserving any manual per-row
		override. Runs here, in the PARENT's validate(), rather than in
		BookedSeat's own validate() — the child table validates before
		the parent's fetch_from fields (price_per_seat, fetched from
		show.ticket_price) are guaranteed to be populated, so reading
		price_per_seat from a child row's context (whether via
		frappe.db.get_value or self.parent_doc) was unreliable and
		silently left seat_price at 0/None. By the time this runs, in
		the parent's own validate(), price_per_seat is reliably set."""
		if not self.price_per_seat:
			return
		for row in self.seats:
			if not row.seat_price:
				row.seat_price = self.price_per_seat

	# ---------- lifecycle helpers ----------

	def adjust_show_seat_counts(self, seats_delta):
		"""Positive delta = seats being booked (on_submit): booked_seats
		increases, available_seats decreases. Negative delta = seats being
		released (on_cancel): the reverse."""
		show = frappe.get_doc("Show", self.show)
		show.db_set("booked_seats", (show.booked_seats or 0) + seats_delta, update_modified=False)
		show.db_set(
			"available_seats", (show.available_seats or 0) - seats_delta, update_modified=False
		)

	def calculate_refund(self):
		"""CUSTOMER-INITIATED cancellation path (fires via formal .cancel(),
		i.e. docstatus 1->2). Applies a TIERED refund based on hours
		between now and the show's start, using thresholds from Booking
		Configuration (MTBX-5) — not hardcoded. Distinct from
		Show.cascade_cancellation_if_cancelled() (MTBX-4.1), which handles
		organization-initiated show cancellations with a flat 100% refund
		instead."""
		config = frappe.get_cached_doc("Booking Configuration")

		show_datetime = get_datetime(f"{self.show_date} {self.start_time}")
		hours_before_show = (show_datetime - now_datetime()).total_seconds() / 3600

		if hours_before_show > config.full_refund_hours:
			refund_pct = 100
		elif hours_before_show >= config.partial_refund_hours:
			refund_pct = config.partial_refund_pct
		else:
			refund_pct = 0

		refund_amount = (self.total_amount or 0) * refund_pct / 100

		self.db_set("refund_amount", refund_amount, update_modified=False)
		self.db_set(
			"payment_status",
			"Refunded" if refund_amount > 0 else "Unpaid",
			update_modified=False,
		)

	def get_or_create_qr_code(self):
		"""Generates a QR code encoding this booking's details and
		attaches it to the record, if not already attached. Returns the
		file_url of the attachment. Called lazily from
		send_booking_confirmation (MTBX-8.4) so the QR is generated once,
		on first request, rather than needing separate generation logic
		wired into every place a confirmation email might be triggered
		(on_submit doc_event, manual button, etc.)."""
		existing = frappe.db.get_value(
			"File",
			{"attached_to_doctype": "Ticket Booking", "attached_to_name": self.name, "file_name": ["like", "qr_%"]},
			"file_url",
		)
		if existing:
			return existing

		import io

		import qrcode

		seat_labels = ", ".join(row.seat_label for row in self.seats)
		qr_content = (
			f"Booking ID: {self.name}\n"
			f"Movie: {self.movie_title}\n"
			f"Theater: {self.theater}\n"
			f"Screen: {self.screen}\n"
			f"Show: {self.show_date} {self.start_time}\n"
			f"Seats: {seat_labels}\n"
			f"Amount: {self.total_amount}"
		)

		img = qrcode.make(qr_content)
		buffer = io.BytesIO()
		img.save(buffer, format="PNG")
		buffer.seek(0)

		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"qr_{self.name}.png",
				"attached_to_doctype": "Ticket Booking",
				"attached_to_name": self.name,
				"content": buffer.read(),
				"is_private": 0,
			}
		)
		file_doc.insert(ignore_permissions=True)

		return file_doc.file_url

	def get_movie_poster(self):
		"""Ticket Booking has no direct Link to Movie (only movie_title,
		a Data field fetched from Show) — resolves the poster via
		Show.movie for use in the MTBX-19 print format."""
		if not self.show:
			return None
		movie = frappe.db.get_value("Show", self.show, "movie")
		if not movie:
			return None
		return frappe.db.get_value("Movie", movie, "poster")


def has_permission(doc, ptype="read", user=None):
	"""Row-level restriction: a user with only the Customer role may read
	their own bookings (booked_by == user), but not others'. Cinema
	Manager and Box Office Staff are unrestricted here — their DocType-
	level permission rules (full/staff CRUD) already grant broader
	access, and this function only needs to narrow things further for
	Customer, not re-grant what those roles already have."""
	user = user or frappe.session.user

	if "Cinema Manager" in frappe.get_roles(user) or "Box Office Staff" in frappe.get_roles(user):
		return True

	if "Customer" in frappe.get_roles(user):
		return doc.booked_by == user

	return True