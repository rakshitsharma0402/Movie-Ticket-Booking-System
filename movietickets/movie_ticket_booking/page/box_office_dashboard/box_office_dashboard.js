// Copyright (c) 2026, Rakshit Sharma and contributors
// For license information, please see license.txt

frappe.pages["box-office-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Box Office Dashboard"),
		single_column: true,
	});

	const $container = $(wrapper).find(".layout-main-section");
	$container.html(`
		<div style="display:grid; grid-template-columns: 1fr 1fr; gap:24px; margin-top:16px;">
			<div id="occupancy-chart"></div>
			<div id="revenue-trend-chart"></div>
			<div id="time-slot-chart"></div>
			<div id="top-movies-chart"></div>
		</div>
	`);

	load_occupancy_chart($container);
	load_revenue_trend_chart($container);
	load_time_slot_chart($container);
	load_top_movies_chart($container);
};

function load_occupancy_chart($container) {
	frappe.call({
		method: "movietickets.api.get_todays_occupancy_by_theater",
		callback: (r) => {
			if (!r.message || !r.message.labels.length) return;
			new frappe.Chart($container.find("#occupancy-chart")[0], {
				title: __("Today's Occupancy by Theater (%)"),
				data: {
					labels: r.message.labels,
					datasets: [{ values: r.message.values }],
				},
				type: "bar",
				height: 260,
			});
		},
	});
}

function load_revenue_trend_chart($container) {
	frappe.call({
		method: "movietickets.api.get_revenue_trend_30_days",
		callback: (r) => {
			if (!r.message || !r.message.labels.length) return;
			new frappe.Chart($container.find("#revenue-trend-chart")[0], {
				title: __("30-Day Revenue Trend"),
				data: {
					labels: r.message.labels,
					datasets: [{ values: r.message.values }],
				},
				type: "line",
				height: 260,
			});
		},
	});
}

function load_time_slot_chart($container) {
	frappe.call({
		method: "movietickets.api.get_bookings_by_time_slot",
		callback: (r) => {
			if (!r.message || !r.message.labels.length) return;
			new frappe.Chart($container.find("#time-slot-chart")[0], {
				title: __("Bookings by Time Slot"),
				data: {
					labels: r.message.labels,
					datasets: [{ values: r.message.values }],
				},
				type: "bar",
				height: 260,
			});
		},
	});
}

function load_top_movies_chart($container) {
	frappe.call({
		method: "movietickets.api.get_top_5_movies_by_bookings",
		callback: (r) => {
			if (!r.message || !r.message.labels.length) return;
			new frappe.Chart($container.find("#top-movies-chart")[0], {
				title: __("Top 5 Movies by Bookings"),
				data: {
					labels: r.message.labels,
					datasets: [{ values: r.message.values }],
				},
				type: "donut",
				height: 260,
			});
		},
	});
}