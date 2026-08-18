// Copyright (c) 2026, Rakshit Sharma and contributors
// For license information, please see license.txt

frappe.ui.form.on("Ticket Booking", {
	refresh(frm) {
		render_show_intro(frm);
		add_select_seats_button(frm);
		add_send_confirmation_button(frm);
	},

	show(frm) {
		render_show_intro(frm);
	},

	before_cancel(frm) {
		// Pauses the cancel action until the user confirms. Returning a
		// Promise from before_cancel is a supported Frappe pattern, but
		// worth a manual test — less commonly exercised than validate/
		// before_save hooks.
		return new Promise((resolve, reject) => {
			frappe.confirm(
				__(
					"Cancelling this booking applies the refund policy: full refund if cancelled more than 4 hours before the show, 50% refund between 2\u20134 hours, and no refund within 2 hours of the show. Do you want to proceed?"
				),
				() => resolve(),
				() => reject()
			);
		});
	},

	// Fires when rows are added to or removed from the "seats" child
	// table — covers both the seat-dialog flow and any manual row
	// add/delete a user does directly in the grid.
	seats_add(frm) {
		recalculate_total(frm);
	},
	seats_remove(frm) {
		recalculate_total(frm);
	},
});

function render_show_intro(frm) {
	frm.set_intro("");
	if (!frm.doc.show) return;

	// available_seats is not a field on Ticket Booking itself (only
	// movie_title/theater/screen/show_date/start_time/price_per_seat are
	// fetched from Show per MTBX-3.1) — a separate fetch is required to
	// show it and to drive the low-seat alert.
	frappe.db.get_doc("Show", frm.doc.show).then((show) => {
		const intro = `
			<b>${frappe.utils.escape_html(show.movie_title || "")}</b><br>
			${frappe.utils.escape_html(show.theater || "")} &mdash; ${frappe.utils.escape_html(show.screen || "")}<br>
			${frappe.datetime.str_to_user(show.show_date)} at ${show.start_time}<br>
			Ticket Price: ${format_currency(show.ticket_price)}<br>
			Available Seats: ${show.available_seats}
		`;
		frm.set_intro(intro, show.available_seats < 5 ? "orange" : "blue");

		if (show.available_seats < 5) {
			frappe.show_alert(
				{
					message: __("Only {0} seats remaining!", [show.available_seats]),
					indicator: "orange",
				},
				5
			);
		}
	});
}

function add_select_seats_button(frm) {
	if (frm.doc.docstatus !== 0) return;
	if (!frm.doc.show) return;

	frm.add_custom_button(__("Select Seats"), () => {
		open_seat_selection_dialog(frm);
	});
}

function open_seat_selection_dialog(frm) {
	frappe.call({
		method: "movietickets.api.get_seat_availability",
		args: { show_name: frm.doc.show },
		callback: (r) => {
			if (!r.message) return;
			render_seat_dialog(frm, r.message);
		},
	});
}

function render_seat_dialog(frm, seat_data) {
	// Seats already saved on this booking are always treated as "mine" /
	// selectable, regardless of the API's booked status — see design
	// note in the ticket write-up about get_seat_availability not
	// excluding this booking's own seats from its query.
	const my_existing_seats = new Set((frm.doc.seats || []).map((r) => r.seat_label));
	const selected = new Set(my_existing_seats);

	const rows_by_letter = {};
	seat_data.seats.forEach((seat) => {
		if (!rows_by_letter[seat.row_letter]) rows_by_letter[seat.row_letter] = [];
		rows_by_letter[seat.row_letter].push(seat);
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Select Seats"),
		size: "large",
		fields: [{ fieldtype: "HTML", fieldname: "seat_grid" }],
		primary_action_label: __("Confirm Selection"),
		primary_action: () => {
			apply_selected_seats(frm, seat_data, selected);
			dialog.hide();
		},
	});

	function draw_grid() {
		let html = `<div style="display:flex; flex-direction:column; gap:6px;">`;

		Object.keys(rows_by_letter)
			.sort()
			.forEach((row_letter) => {
				html += `<div style="display:flex; gap:4px; align-items:center; flex-wrap:wrap;">
					<span style="width:24px; font-weight:bold;">${row_letter}</span>`;

				rows_by_letter[row_letter].forEach((seat) => {
					const is_booked_by_other =
						seat.status === "booked" && !my_existing_seats.has(seat.seat_label);
					const is_selected = selected.has(seat.seat_label);

					let bg = "#28a745"; // available, unselected
					if (is_booked_by_other) bg = "#dc3545"; // booked by someone else
					else if (is_selected) bg = "#007bff"; // currently selected

					html += `
						<button
							type="button"
							class="seat-btn"
							data-seat="${seat.seat_label}"
							${is_booked_by_other ? "disabled" : ""}
							style="width:28px;height:28px;font-size:10px;border:none;border-radius:4px;
								color:white;background:${bg};
								cursor:${is_booked_by_other ? "not-allowed" : "pointer"};"
							title="${seat.seat_label}"
						>${seat.seat_number}</button>
					`;
				});
				html += `</div>`;
			});

		html += `</div>
			<div style="margin-top:10px; font-size:12px;">
				<span style="color:#28a745;">\u25A0</span> Available &nbsp;
				<span style="color:#007bff;">\u25A0</span> Selected &nbsp;
				<span style="color:#dc3545;">\u25A0</span> Booked
			</div>`;

		dialog.fields_dict.seat_grid.$wrapper.html(html);

		dialog.fields_dict.seat_grid.$wrapper.find(".seat-btn:not(:disabled)").on("click", function () {
			const seat_label = $(this).data("seat");
			if (selected.has(seat_label)) {
				selected.delete(seat_label);
			} else {
				selected.add(seat_label);
			}
			draw_grid();
		});
	}

	draw_grid();
	dialog.show();
}

function apply_selected_seats(frm, seat_data, selected) {
	frm.clear_table("seats");

	const seat_lookup = {};
	seat_data.seats.forEach((s) => (seat_lookup[s.seat_label] = s));

	selected.forEach((seat_label) => {
		const seat = seat_lookup[seat_label];
		if (!seat) return;
		const row = frm.add_child("seats");
		row.seat_label = seat.seat_label;
		row.row_letter = seat.row_letter;
		row.seat_number = seat.seat_number;
		// seat_price intentionally left blank — Booked Seat's own
		// controller (MTBX-3.2) defaults it from the parent's
		// price_per_seat on save, preserving any manual per-seat
		// override made afterward in the grid.
	});

	frm.refresh_field("seats");
	recalculate_total(frm);
}

function recalculate_total(frm) {
	// Mirrors TicketBooking.calculate_totals() (MTBX-4.2) exactly:
	// number_of_seats * price_per_seat. NOTE: this does NOT sum
	// individual seat_price overrides from the child table, even though
	// MTBX-3.2 designed seat_price to support premium per-seat pricing.
	// That inconsistency already exists server-side; flagged for a
	// decision rather than fixed unilaterally here.
	const num_seats = (frm.doc.seats || []).length;
	const price = frm.doc.price_per_seat || 0;
	frm.set_value("number_of_seats", num_seats);
	frm.set_value("total_amount", num_seats * price);
}

function add_send_confirmation_button(frm) {
	if (frm.doc.docstatus !== 1) return;

	frm.add_custom_button(__("Send Booking Confirmation"), () => {
		frappe.call({
			method: "movietickets.api.send_booking_confirmation",
			args: { booking_name: frm.doc.name },
			freeze: true,
			freeze_message: __("Sending confirmation email..."),
			callback: (r) => {
				if (r.message && r.message.success) {
					frappe.show_alert({ message: r.message.message, indicator: "green" }, 5);
				}
			},
		});
	});
}