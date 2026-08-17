@frappe.whitelist()
def get_seat_availability(show_name):
	"""Returns a 2D seat-grid representation for a Show, for the seat-
	selection dialog on Ticket Booking (MTBX-7.1).

	Row letters are derived the same way as TicketBooking's own
	seat_label validation (MTBX-4.2): row 1 = A, row 2 = B, etc., up to
	the Screen's seat_rows count. "Booked" means a seat appears in the
	Booked Seat child table of any Ticket Booking for this Show whose
	booking_status is Pending or Confirmed — mirrors the exact filter
	used in TicketBooking.validate_seats_not_already_booked, so the
	dialog's red/green rendering always agrees with what create_booking
	will actually accept or reject.

	Returns:
		{
			"seat_rows": int,
			"seats_per_row": int,
			"seats": [
				{"seat_label": "A-1", "row_letter": "A", "seat_number": 1, "status": "available"},
				{"seat_label": "A-2", "row_letter": "A", "seat_number": 2, "status": "booked"},
				...
			]
		}
	"""
	if not show_name:
		frappe.throw("show_name is required.")

	show = frappe.db.get_value("Show", show_name, ["screen"], as_dict=True)
	if not show:
		frappe.throw(f"Show '{show_name}' not found.")

	seat_rows, seats_per_row = frappe.db.get_value(
		"Screen", show.screen, ["seat_rows", "seats_per_row"]
	)

	if seat_rows > 26:
		frappe.throw(
			f"Screen has {seat_rows} rows — seat labeling only supports up to 26 (A-Z).",
			title="Unsupported Screen Configuration",
		)

	booked_labels = set(
		frappe.db.sql(
			"""
			SELECT bs.seat_label
			FROM `tabBooked Seat` bs
			INNER JOIN `tabTicket Booking` tb ON tb.name = bs.parent
			WHERE tb.show = %(show_name)s
			  AND tb.booking_status IN ('Pending', 'Confirmed')
			""",
			{"show_name": show_name},
			pluck="seat_label",
		)
	)

	seats = []
	for row_index in range(seat_rows):
		row_letter = chr(ord("A") + row_index)
		for seat_number in range(1, seats_per_row + 1):
			seat_label = f"{row_letter}-{seat_number}"
			seats.append(
				{
					"seat_label": seat_label,
					"row_letter": row_letter,
					"seat_number": seat_number,
					"status": "booked" if seat_label in booked_labels else "available",
				}
			)

	return {
		"seat_rows": seat_rows,
		"seats_per_row": seats_per_row,
		"seats": seats,
	}