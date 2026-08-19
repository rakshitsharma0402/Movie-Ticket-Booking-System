# Copyright (c) 2026, Rakshit Sharma and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_to_date, getdate, now_datetime

# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]


class IntegrationTestTicketBooking(IntegrationTestCase):
	"""
	Integration tests for TicketBooking.
	Covers booking/refund/cancellation lifecycle.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.genre = cls._get_or_create_genre()
		cls.movie = cls._get_or_create_movie(cls.genre)
		cls.theater = cls._get_or_create_theater()
		cls._pin_booking_configuration()

	@classmethod
	def _pin_booking_configuration(cls):
		"""Refund tests (5/6/7) depend on exact threshold values. Pinning
		them here makes the tests deterministic regardless of whatever is
		currently seeded in Booking Configuration, rather than trusting
		production/dev data to stay unchanged."""
		config = frappe.get_single("Booking Configuration")
		config.max_seats_per_booking = 10
		config.full_refund_hours = 4
		config.partial_refund_hours = 2
		config.partial_refund_pct = 50
		config.save(ignore_permissions=True)

	@classmethod
	def _get_or_create_genre(cls):
		name = "Test Genre MTBX15"
		if frappe.db.exists("Movie Genre", name):
			return name
		frappe.get_doc(
			{"doctype": "Movie Genre", "genre_name": name, "is_active": 1}
		).insert(ignore_permissions=True)
		return name

	@classmethod
	def _get_or_create_movie(cls, genre):
		existing = frappe.db.get_value("Movie", {"title": "Test Movie MTBX15"}, "name")
		if existing:
			return existing
		movie = frappe.get_doc(
			{
				"doctype": "Movie",
				"naming_series": "MOV-.#####",
				"title": "Test Movie MTBX15",
				"language": "English",
				"genre": genre,
				"duration_minutes": 150,
				"release_date": getdate(),
				"rating": "UA",
			}
		)
		movie.insert(ignore_permissions=True)
		return movie.name

	@classmethod
	def _get_or_create_theater(cls):
		name = "Test Theater MTBX15 - Test City"
		if frappe.db.exists("Theater", name):
			return name
		theater = frappe.get_doc(
			{
				"doctype": "Theater",
				"theater_name": "Test Theater MTBX15",
				"city": "Test City",
				"address": "123 Test Street",
				"is_active": 1,
			}
		)
		theater.insert(ignore_permissions=True)
		return theater.name

	def _create_screen(self, seat_rows=10, seats_per_row=10, base_price=200):
		"""Each call creates a fresh, uniquely-named Screen, so tests
		never share a screen and therefore can never accidentally trip
		each other's overlap-conflict validation."""
		screen = frappe.get_doc(
			{
				"doctype": "Screen",
				"screen_name": f"Screen {frappe.generate_hash(length=6)}",
				"theater": self.theater,
				"screen_type": "Standard",
				"seat_rows": seat_rows,
				"seats_per_row": seats_per_row,
				"total_seats": seat_rows * seats_per_row,
				"base_price": base_price,
				"is_active": 1,
			}
		)
		screen.insert(ignore_permissions=True)
		return screen.name

	def _create_show(self, screen=None, show_date=None, start_time="10:00:00", seat_rows=10, seats_per_row=10):
		if screen is None:
			screen = self._create_screen(seat_rows=seat_rows, seats_per_row=seats_per_row)
		show = frappe.get_doc(
			{
				"doctype": "Show",
				"naming_series": "SHW-.YYYY.-.#####",
				"movie": self.movie,
				"screen": screen,
				"show_date": show_date or getdate(),
				"start_time": start_time,
			}
		)
		show.insert(ignore_permissions=True)
		return show

	def _seat_labels(self, count, seats_per_row):
		labels = []
		row, seat = 0, 1
		for _ in range(count):
			labels.append(f"{chr(ord('A') + row)}-{seat}")
			seat += 1
			if seat > seats_per_row:
				seat, row = 1, row + 1
		return labels

	def _make_booking(self, show, seat_labels, customer_suffix="1"):
		seats = []
		for label in seat_labels:
			row_letter, seat_number = label.split("-")
			seats.append({"seat_label": label, "row_letter": row_letter, "seat_number": int(seat_number)})

		booking = frappe.get_doc(
			{
				"doctype": "Ticket Booking",
				"naming_series": "BKG-.YYYY.-.#####",
				"show": show.name,
				"customer_name": f"Test Customer {customer_suffix}",
				"customer_email": f"test{customer_suffix}@example.com",
				"customer_phone": "9000000000",
				"seats": seats,
			}
		)
		booking.insert(ignore_permissions=True)
		return booking

	def test_booking_decreases_available_seats(self):
		"""Create a show with 100 seats. Book 3 seats. Assert
		available_seats=97, booked_seats=3.

		NOTE: seat counts only update on submit (MTBX-4.2's on_submit ->
		adjust_show_seat_counts), not on plain insert — so this test
		submits the booking even though the ticket title doesn't say so,
		matching the system's actual, already-verified behavior."""
		show = self._create_show(seat_rows=10, seats_per_row=10)
		booking = self._make_booking(show, self._seat_labels(3, 10))
		booking.submit()

		show.reload()
		self.assertEqual(show.available_seats, 97)
		self.assertEqual(show.booked_seats, 3)

	def test_cannot_book_already_taken_seat(self):
		show = self._create_show(seat_rows=10, seats_per_row=10)
		self._make_booking(show, ["A-1"], customer_suffix="a")

		with self.assertRaises(frappe.ValidationError):
			self._make_booking(show, ["A-1"], customer_suffix="b")

	def test_cannot_book_for_cancelled_show(self):
		show = self._create_show(seat_rows=10, seats_per_row=10)
		show.show_status = "Cancelled"
		show.save(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			self._make_booking(show, ["B-1"])

	def test_max_seats_per_booking_limit(self):
		show = self._create_show(seat_rows=10, seats_per_row=10)
		with self.assertRaises(frappe.ValidationError):
			self._make_booking(show, self._seat_labels(11, 10))

	def test_full_refund_on_early_cancellation(self):
		start_dt = add_to_date(now_datetime(), hours=6)
		show = self._create_show(
			show_date=start_dt.date(),
			start_time=start_dt.strftime("%H:%M:%S"),
			seat_rows=10,
			seats_per_row=10,
		)
		booking = self._make_booking(show, self._seat_labels(2, 10))
		booking.submit()
		booking.cancel()
		booking.reload()

		self.assertEqual(booking.refund_amount, booking.total_amount)

	def test_partial_refund_on_late_cancellation(self):
		start_dt = add_to_date(now_datetime(), hours=3)
		show = self._create_show(
			show_date=start_dt.date(),
			start_time=start_dt.strftime("%H:%M:%S"),
			seat_rows=10,
			seats_per_row=10,
		)
		booking = self._make_booking(show, self._seat_labels(2, 10))
		booking.submit()
		booking.cancel()
		booking.reload()

		self.assertEqual(booking.refund_amount, booking.total_amount * 0.5)

	def test_no_refund_on_very_late_cancellation(self):
		start_dt = add_to_date(now_datetime(), hours=1)
		show = self._create_show(
			show_date=start_dt.date(),
			start_time=start_dt.strftime("%H:%M:%S"),
			seat_rows=10,
			seats_per_row=10,
		)
		booking = self._make_booking(show, self._seat_labels(2, 10))
		booking.submit()
		booking.cancel()
		booking.reload()

		self.assertEqual(booking.refund_amount, 0)

	def test_show_conflict_validation(self):
		screen = self._create_screen(seat_rows=10, seats_per_row=10)
		show_date = getdate()
		self._create_show(screen=screen, show_date=show_date, start_time="14:00:00")

		with self.assertRaises(frappe.ValidationError):
			self._create_show(screen=screen, show_date=show_date, start_time="15:00:00")

	def test_cancel_restores_seats(self):
		show = self._create_show(seat_rows=10, seats_per_row=10)
		booking = self._make_booking(show, self._seat_labels(4, 10))
		booking.submit()

		show.reload()
		self.assertEqual(show.available_seats, 96)

		booking.cancel()
		show.reload()
		self.assertEqual(show.available_seats, 100)


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

	