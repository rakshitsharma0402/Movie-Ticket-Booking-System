# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe

no_cache = 1


def get_context(context):
	frappe.log_error("NOW-SHOWING DEBUG: get_context called", "now-showing-debug")
	"""Guest-accessible landing page: card grid of Now Showing movies,
	filterable by genre/language. No whitelisted API exists for this
	specific query (MTBX-8's five APIs cover seat availability, booking,
	shows-for-movie, confirmation email, revenue — not movie listing),
	so this queries directly via frappe.db.get_all, matching the pattern
	used elsewhere for read-only portal data."""
	context.no_cache = 1

	genre = frappe.form_dict.get("genre")
	language = frappe.form_dict.get("language")

	filters = {"movie_status": "Now Showing"}
	if genre:
		filters["genre"] = genre
	if language:
		filters["language"] = language

	context.movies = frappe.db.get_all(
		"Movie",
		filters=filters,
		fields=["name", "title", "language", "genre", "rating", "duration_minutes", "poster"],
		order_by="title asc",
	)

	context.genres = frappe.db.get_all("Movie Genre", filters={"is_active": 1}, pluck="genre_name")
	context.languages = frappe.db.get_all(
		"Movie", filters={"movie_status": "Now Showing"}, pluck="language", distinct=True
	)

	context.selected_genre = genre
	context.selected_language = language