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
};