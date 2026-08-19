# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict

no_cache = 1


def get_context(context):
	"""Shows upcoming screenings for a selected movie, grouped by
	theater then date. Reuses the existing get_shows_for_movie API
	(MTBX-8.3) rather than re-querying directly, so this page always
	reflects the exact same 'upcoming' definition as the API."""
	context.no_cache = 1

	movie_name = frappe.form_dict.get("movie")
	if not movie_name:
		frappe.throw("Movie not specified.", frappe.DoesNotExistError)

	movie = frappe.db.get_value(
		"Movie", movie_name, ["title", "language", "genre", "rating", "poster"], as_dict=True
	)
	if not movie:
		frappe.throw(f"Movie '{movie_name}' not found.", frappe.DoesNotExistError)

	context.movie = movie
	context.movie_name = movie_name

	from movietickets.api import get_shows_for_movie

	shows = get_shows_for_movie(movie=movie_name)

	# Group by theater, then by date, preserving the API's date/time sort order.
	grouped = defaultdict(lambda: defaultdict(list))
	for show in shows:
		grouped[show["theater"]][str(show["show_date"])].append(show)

	context.grouped_shows = grouped
	context.is_guest = frappe.session.user == "Guest"