// Copyright (c) 2026, Rakshit Sharma and contributors
// For license information, please see license.txt

frappe.query_reports["Box Office Collection Report"] = {
	filters: [
		{
			fieldname: "theater",
			label: __("Theater"),
			fieldtype: "Link",
			options: "Theater",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
		},
		{
			fieldname: "genre",
			label: __("Genre"),
			fieldtype: "Link",
			options: "Movie Genre",
		},
		{
			fieldname: "language",
			label: __("Language"),
			fieldtype: "Select",
			options: "\nEnglish\nHindi\nGujarati\nTamil\nTelugu\nOther",
		},
	],

	onload(report) {
		render_screen_type_pie_chart(report);
	},

	after_datatable_render(datatable) {
		// Filters can change after initial load; re-render the pie chart
		// whenever the report's data refreshes so it stays in sync.
		render_screen_type_pie_chart(frappe.query_report);
	},
};

function render_screen_type_pie_chart(report) {
	if (!report || !report.page) return;

	frappe.call({
		method:
			"movietickets.movie_ticket_booking.report.box_office_collection_report.box_office_collection_report.get_screen_type_revenue",
		args: { filters: report.get_values ? report.get_values() : {} },
		callback: (r) => {
			if (!r.message) return;

			let $wrapper = report.page.main.find(".screen-type-pie-chart-wrapper");
			if (!$wrapper.length) {
				$wrapper = $('<div class="screen-type-pie-chart-wrapper" style="margin: 16px 0;"></div>');
				report.page.main.find(".report-wrapper").after($wrapper);
			}
			$wrapper.empty();

			if (!r.message.labels.length) return;

			new frappe.Chart($wrapper[0], {
				title: __("Revenue by Screen Type"),
				data: {
					labels: r.message.labels,
					datasets: [{ values: r.message.values }],
				},
				type: "pie",
				height: 260,
			});
		},
	});
}