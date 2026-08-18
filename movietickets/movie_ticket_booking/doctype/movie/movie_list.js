// Copyright (c) 2026, Rakshit Sharma and contributors
// For license information, please see license.txt

frappe.listview_settings["Movie"] = {
	add_fields: ["title", "language", "genre", "rating", "release_date", "movie_status"],
	get_indicator(doc) {
		const status_map = {
			"Now Showing": "green",
			"Upcoming": "blue",
			"Ended": "gray",
		};
		return [__(doc.movie_status), status_map[doc.movie_status] || "gray", "movie_status,=," + doc.movie_status];
	},
};