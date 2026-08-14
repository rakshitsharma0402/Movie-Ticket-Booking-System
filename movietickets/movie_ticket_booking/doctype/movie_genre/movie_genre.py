# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MovieGenre(Document):
    def validate(self):
        self.validate_duplicate_genre_name()

    def validate_duplicate_genre_name(self):
        """Case-insensitive check that no other Movie Genre record
        shares this genre_name."""
        if not self.genre_name:
            return

        existing = frappe.db.sql(
            """
            SELECT name
            FROM `tabMovie Genre`
            WHERE LOWER(genre_name) = LOWER(%s)
              AND name != %s
            """,
            (self.genre_name, self.name or ""),
        )

        if existing:
            frappe.throw(
                "A Movie Genre with the name '{0}' already exists ({1}). "
                "Genre names must be unique regardless of case.".format(
                    self.genre_name, existing[0][0]
                ),
                title="Duplicate Genre Name",
            )