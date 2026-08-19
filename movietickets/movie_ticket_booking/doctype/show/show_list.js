// Copyright (c) 2026, Rakshit Sharma and contributors
// For license information, please see license.txt

frappe.listview_settings["Show"] = {
	add_fields: ["movie_title", "screen", "show_date", "start_time", "available_seats", "show_status"],
	get_indicator(doc) {
		const status_map = {
			Scheduled: "green",
			"Now Playing": "orange",
			Completed: "gray",
			Cancelled: "red",
		};
		return [__(doc.show_status), status_map[doc.show_status] || "gray", "show_status,=," + doc.show_status];
	},

	onload(listview) {
		listview.page.add_inner_button(__("Bulk Create Shows"), () => {
			open_bulk_show_dialog();
		});
	},
};

function open_bulk_show_dialog() {
	const dialog = new frappe.ui.Dialog({
		title: __("Bulk Create Shows"),
		fields: [
			{ fieldtype: "Link", fieldname: "movie", label: __("Movie"), options: "Movie", reqd: 1 },
			{
				fieldtype: "MultiSelectList",
				fieldname: "screens",
				label: __("Screens"),
				get_data: function (txt) {
					return frappe.db.get_link_options("Screen", txt);
				},
				reqd: 1,
			},
			{ fieldtype: "Date", fieldname: "date_from", label: __("From Date"), reqd: 1 },
			{ fieldtype: "Date", fieldname: "date_to", label: __("To Date"), reqd: 1 },
			{
				fieldtype: "Small Text",
				fieldname: "show_times",
				label: __("Show Times (one per line, HH:MM:SS)"),
				reqd: 1,
				description: __("e.g. 10:00:00"),
			},
		],
		primary_action_label: __("Create Shows"),
		primary_action: (values) => {
			const show_times = values.show_times
				.split("\n")
				.map((t) => t.trim())
				.filter((t) => t);

			frappe.call({
				method: "movietickets.api.create_shows_bulk",
				args: {
					movie: values.movie,
					screens: values.screens,
					date_from: values.date_from,
					date_to: values.date_to,
					show_times: show_times,
				},
				callback: (r) => {
					if (r.message && r.message.success) {
						frappe.show_alert({ message: r.message.message, indicator: "blue" }, 5);
						dialog.hide();
					}
				},
			});
		},
	});

	dialog.show();
}

// Listens for the background job's completion, wherever the user is
// in the Desk when it fires — not scoped only to the dialog's
// lifetime, since the job may finish well after the dialog is closed.
frappe.realtime.on("bulk_show_creation_complete", (data) => {
	const created_count = data.created.length;
	const failed_count = data.failed.length;

	let message = __("Bulk show creation finished: {0} created", [created_count]);
	if (failed_count > 0) {
		message += __(", {0} skipped due to conflicts", [failed_count]);
	}

	frappe.show_alert(
		{ message, indicator: failed_count > 0 ? "orange" : "green" },
		8
	);

	if (failed_count > 0) {
		console.log("Bulk show creation — skipped shows:", data.failed);
	}
});

