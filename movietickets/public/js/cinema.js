// Copyright (c) 2026, Rakshit Sharma and contributors

console.log("Movie Tickets App Loaded");

frappe.provide("movietickets");

document.addEventListener("keydown", function (e) {
	// Ctrl+Shift+B — quick-open a new Ticket Booking form
	if (e.ctrlKey && e.shiftKey && e.key.toUpperCase() === "B") {
		e.preventDefault();
		frappe.new_doc("Ticket Booking");
	}
});

