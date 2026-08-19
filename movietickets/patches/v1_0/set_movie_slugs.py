# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Backfills slug for any Movie where it's NULL or empty, by
	reusing Movie.generate_slug() (MTBX-1.2) directly — that method
	already computes correctly when slug is empty, regardless of
	whether title has changed, so no separate slug logic is needed
	here."""
	movies = frappe.get_all(
		"Movie", filters=[["slug", "in", ["", None]]], pluck="name"
	)

	for movie_name in movies:
		movie = frappe.get_doc("Movie", movie_name)
		movie.generate_slug()

		if movie.slug:
			frappe.db.set_value("Movie", movie_name, "slug", movie.slug, update_modified=False)

	frappe.db.commit()

    