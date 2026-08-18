// Copyright (c) 2026, Rakshit Sharma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Show", {
	refresh(frm) {
		add_view_bookings_button(frm);
		render_occupancy_dashboard(frm);
	},

	screen(frm) {
		auto_fetch_ticket_price(frm);
		preview_end_time(frm);
	},

	movie(frm) {
		preview_end_time(frm);
	},

	start_time(frm) {
		preview_end_time(frm);
	},
});

function auto_fetch_ticket_price(frm) {
	if (!frm.doc.screen) return;
	// Client-side preview only, before save — mirrors the "only fill if
	// empty" behavior of Show.set_ticket_price_default() (MTBX-4.1),
	// which does the real, authoritative default server-side at
	// before_insert. This just avoids clobbering a price the user
	// already typed in before picking/changing the screen.
	if (frm.doc.ticket_price) return;

	frappe.db.get_value("Screen", frm.doc.screen, "base_price").then((r) => {
		if (r.message && r.message.base_price) {
			frm.set_value("ticket_price", r.message.base_price);
		}
	});
}

function preview_end_time(frm) {
	if (!frm.doc.movie || !frm.doc.start_time) return;

	frappe.db.get_value("Movie", frm.doc.movie, "duration_minutes").then((r) => {
		const duration = r.message && r.message.duration_minutes;
		if (!duration) return;

		// start_time comes back as "HH:MM:SS"; do the arithmetic in
		// minutes-since-midnight rather than constructing a Date object,
		// to avoid timezone/date-boundary edge cases entirely client-side.
		const [h, m, s] = frm.doc.start_time.split(":").map(Number);
		const start_minutes = h * 60 + m;
		const end_minutes = (start_minutes + duration) % (24 * 60);
		const end_h = String(Math.floor(end_minutes / 60)).padStart(2, "0");
		const end_m = String(end_minutes % 60).padStart(2, "0");

		frappe.show_alert(
			{
				message: __("Estimated end time: {0}", [`${end_h}:${end_m}`]),
				indicator: "blue",
			},
			5
		);
	});
}

function add_view_bookings_button(frm) {
	if (frm.is_new()) return;

	frm.add_custom_button(__("View Bookings"), () => {
		frappe.set_route("List", "Ticket Booking", { show: frm.doc.name });
	});
}

function render_occupancy_dashboard(frm) {
	if (frm.is_new()) return;

	const total = frm.doc.total_seats || 0;
	const booked = frm.doc.booked_seats || 0;
	const available = frm.doc.available_seats || 0;
	const occupancy_pct = total > 0 ? Math.round((booked / total) * 1000) / 10 : 0;

	frm.dashboard.add_indicator(__("Booked: {0}", [booked]), "blue");
	frm.dashboard.add_indicator(__("Available: {0}", [available]), "green");

	let occupancy_color = "green";
	if (occupancy_pct >= 100) occupancy_color = "red";
	else if (occupancy_pct > 80) occupancy_color = "orange";

	frm.dashboard.add_indicator(__("Occupancy: {0}%", [occupancy_pct]), occupancy_color);
}