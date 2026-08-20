# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

"""Seeds demo/sample data for a fresh install — movies, theaters, screens,
shows (dated relative to today so they never go stale), sample bookings,
and the three demo role users. Safe to re-run; skips anything that
already exists.

Run with:
    bench --site <site-name> execute movietickets.demo_data.run
"""

import frappe


def run():
	seed_genres()
	seed_movies()
	seed_theaters()
	seed_screens()
	seed_shows()
	seed_sample_bookings()
	seed_booking_configuration()
	seed_demo_users()
	frappe.db.commit()
	print("Demo data seeded successfully.")


def seed_genres():
	genres = [
		("Action", "High-energy films with stunts, fights, and chases"),
		("Comedy", "Films designed to make the audience laugh"),
		("Drama", "Serious narrative-driven films focused on emotions"),
		("Horror", "Films intended to frighten and create suspense"),
		("Sci-Fi", "Science fiction with futuristic themes and technology"),
		("Romance", "Films focused on love stories and relationships"),
		("Thriller", "Suspenseful films with tension and plot twists"),
		("Animation", "Animated feature films for all ages"),
	]
	for genre_name, description in genres:
		if not frappe.db.exists("Movie Genre", genre_name):
			frappe.get_doc({
				"doctype": "Movie Genre", "genre_name": genre_name,
				"description": description, "is_active": 1,
			}).insert()


def seed_movies():
	today = frappe.utils.today()
	movies = [
		dict(title="Inception", language="English", genre="Sci-Fi", duration_minutes=148,
			release_date=frappe.utils.add_days(today, -10), end_date=frappe.utils.add_days(today, 60),
			rating="UA", director="Christopher Nolan"),
		dict(title="Pushpa 3: The Rampage", language="Hindi", genre="Action", duration_minutes=165,
			release_date=frappe.utils.add_days(today, -5), end_date=frappe.utils.add_days(today, 45),
			rating="UA", director="Sukumar"),
		dict(title="Stree 3", language="Hindi", genre="Comedy", duration_minutes=140,
			release_date=frappe.utils.add_days(today, -3), end_date=frappe.utils.add_days(today, 40),
			rating="UA", director="Amar Kaushik"),
		dict(title="The Conjuring 4", language="English", genre="Horror", duration_minutes=130,
			release_date=frappe.utils.add_days(today, -1), end_date=frappe.utils.add_days(today, 50),
			rating="A", director="Michael Chaves"),
		dict(title="Chhello Show 2", language="Gujarati", genre="Drama", duration_minutes=120,
			release_date=frappe.utils.add_days(today, -7), end_date=frappe.utils.add_days(today, 30),
			rating="U", director="Pan Nalin"),
		dict(title="Robot 3.0", language="Tamil", genre="Sci-Fi", duration_minutes=155,
			release_date=frappe.utils.add_days(today, 5), rating="UA", director="S. Shankar"),
	]
	for m in movies:
		if not frappe.db.exists("Movie", {"title": m["title"]}):
			frappe.get_doc({"doctype": "Movie", "naming_series": "MOV-.#####", **m}).insert()


def seed_theaters():
	theaters = [
		dict(theater_name="PVR IMAX", city="Ahmedabad",
			address="Acropolis Mall, SG Highway, Ahmedabad 380054", phone="07940012034"),
		dict(theater_name="INOX Megaplex", city="Ahmedabad",
			address="Gujarat Science City Road, Ahmedabad 380060", phone="07940005678"),
		dict(theater_name="Rajhans Cineplex", city="Surat",
			address="Piplod, Surat 395007", phone="02612345678"),
		dict(theater_name="Cinepolis", city="Gandhinagar",
			address="Infocity, Gandhinagar 382009", phone="07923456789"),
	]
	for t in theaters:
		name = f"{t['theater_name']} - {t['city']}"
		if not frappe.db.exists("Theater", name):
			frappe.get_doc({"doctype": "Theater", "is_active": 1, **t}).insert()


def seed_screens():
	screens = [
		dict(screen_name="Screen 1", theater="PVR IMAX - Ahmedabad", screen_type="IMAX",
			seat_rows=12, seats_per_row=20, total_seats=240, base_price=450.00),
		dict(screen_name="Screen 2", theater="PVR IMAX - Ahmedabad", screen_type="Standard",
			seat_rows=10, seats_per_row=15, total_seats=150, base_price=250.00),
		dict(screen_name="Screen 3", theater="PVR IMAX - Ahmedabad", screen_type="3D",
			seat_rows=10, seats_per_row=18, total_seats=180, base_price=350.00),
		dict(screen_name="Audi 1", theater="INOX Megaplex - Ahmedabad", screen_type="Standard",
			seat_rows=10, seats_per_row=16, total_seats=160, base_price=220.00),
		dict(screen_name="Audi 2", theater="INOX Megaplex - Ahmedabad", screen_type="4DX",
			seat_rows=8, seats_per_row=12, total_seats=96, base_price=500.00),
		dict(screen_name="Screen 1", theater="Rajhans Cineplex - Surat", screen_type="Standard",
			seat_rows=12, seats_per_row=20, total_seats=240, base_price=180.00),
		dict(screen_name="Screen 2", theater="Rajhans Cineplex - Surat", screen_type="3D",
			seat_rows=10, seats_per_row=15, total_seats=150, base_price=280.00),
		dict(screen_name="Screen 1", theater="Cinepolis - Gandhinagar", screen_type="Standard",
			seat_rows=10, seats_per_row=18, total_seats=180, base_price=200.00),
	]
	for s in screens:
		theater_short = s["theater"].split(" - ")[0]
		generated_name = f"{theater_short}-{s['screen_name']}"
		if not frappe.db.exists("Screen", generated_name):
			frappe.get_doc({"doctype": "Screen", "is_active": 1, **s}).insert()


def seed_shows():
	today = frappe.utils.today()
	shows_to_create = [
		dict(movie_title="Inception", screen="PVR IMAX-Screen 1", show_date=today,
			start_time="10:00:00", ticket_price=450.00),
		dict(movie_title="Inception", screen="PVR IMAX-Screen 1", show_date=today,
			start_time="18:30:00", ticket_price=500.00),
		dict(movie_title="Pushpa 3: The Rampage", screen="PVR IMAX-Screen 2", show_date=today,
			start_time="09:30:00", ticket_price=300.00),
		dict(movie_title="Stree 3", screen="INOX Megaplex-Audi 1", show_date=today,
			start_time="12:00:00", ticket_price=250.00),
		dict(movie_title="The Conjuring 4", screen="INOX Megaplex-Audi 2",
			show_date=frappe.utils.add_days(today, 1), start_time="21:00:00", ticket_price=500.00),
		dict(movie_title="Chhello Show 2", screen="Rajhans Cineplex-Screen 2",
			show_date=frappe.utils.add_days(today, 1), start_time="16:00:00", ticket_price=280.00),
		dict(movie_title="Robot 3.0", screen="Cinepolis-Screen 1",
			show_date=frappe.utils.add_days(today, 6), start_time="13:00:00", ticket_price=250.00),
	]

	frappe.flags.created_shows = []
	for s in shows_to_create:
		movie_name = frappe.db.get_value("Movie", {"title": s["movie_title"]}, "name")
		if not movie_name or not frappe.db.exists("Screen", s["screen"]):
			continue
		# Skip if an identical show already exists (idempotency, since
		# Shows don't have a natural unique key across the fields we care about)
		existing = frappe.db.exists("Show", {
			"movie": movie_name, "screen": s["screen"],
			"show_date": s["show_date"], "start_time": s["start_time"],
		})
		if existing:
			frappe.flags.created_shows.append(frappe.get_doc("Show", existing))
			continue
		show = frappe.get_doc({
			"doctype": "Show", "naming_series": "SHW-.YYYY.-.#####",
			"movie": movie_name, "screen": s["screen"], "show_date": s["show_date"],
			"start_time": s["start_time"], "ticket_price": s["ticket_price"],
		})
		show.insert()
		frappe.flags.created_shows.append(show)


def seed_sample_bookings():
	created_shows = frappe.flags.get("created_shows", [])
	sample_bookings = [
		dict(show_index=0, customer_name="Ravi Patel", customer_email="ravi@example.com",
			customer_phone="9876543210", seats=["A-5", "A-6", "A-7"]),
		dict(show_index=0, customer_name="Priya Shah", customer_email="priya@example.com",
			customer_phone="9876543211", seats=["C-10", "C-11"]),
		dict(show_index=2, customer_name="Amit Kumar", customer_email="amit@example.com",
			customer_phone="9876543212", seats=["B-1", "B-2", "B-3"]),
		dict(show_index=3, customer_name="Neha Desai", customer_email="neha@example.com",
			customer_phone="9876543213", seats=["D-8", "D-9"]),
	]

	for b in sample_bookings:
		if b["show_index"] >= len(created_shows):
			continue
		show_name = created_shows[b["show_index"]].name

		if frappe.db.exists("Ticket Booking", {"customer_email": b["customer_email"], "show": show_name}):
			continue

		seats = []
		for label in b["seats"]:
			row_letter, seat_number = label.split("-")
			seats.append({"seat_label": label, "row_letter": row_letter, "seat_number": int(seat_number)})

		try:
			booking = frappe.get_doc({
				"doctype": "Ticket Booking", "naming_series": "BKG-.YYYY.-.#####",
				"show": show_name, "customer_name": b["customer_name"],
				"customer_email": b["customer_email"], "customer_phone": b["customer_phone"],
				"seats": seats,
			})
			booking.insert()
			booking.submit()
		except frappe.ValidationError:
			# Seats may already be taken by a previous partial run; skip.
			continue


def seed_booking_configuration():
	config = frappe.get_single("Booking Configuration")
	config.max_seats_per_booking = 10
	config.booking_expiry_minutes = 15
	config.full_refund_hours = 4
	config.partial_refund_hours = 2
	config.partial_refund_pct = 50
	config.enable_auto_expiry = 1
	config.booking_open_days_before = 7
	config.save()


def seed_demo_users():
	users = [
		dict(email="manager@test.com", full_name="Rajesh Manager", role="Cinema Manager", user_type="System User"),
		dict(email="staff@test.com", full_name="Pooja Staff", role="Box Office Staff", user_type="System User"),
		dict(email="customer@test.com", full_name="Vikram Customer", role="Customer", user_type="Website User"),
	]
	for u in users:
		if frappe.db.exists("User", u["email"]):
			continue
		user_doc = frappe.get_doc({
			"doctype": "User", "email": u["email"],
			"first_name": u["full_name"].split()[0],
			"last_name": " ".join(u["full_name"].split()[1:]),
			"send_welcome_email": 0, "user_type": u["user_type"],
			"new_password": "Demo@1234",
		})
		user_doc.insert(ignore_permissions=True)
		user_doc.add_roles(u["role"])