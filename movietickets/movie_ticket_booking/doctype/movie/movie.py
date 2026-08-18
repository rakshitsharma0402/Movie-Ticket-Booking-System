# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

import re
from datetime import date

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class Movie(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        director: DF.Data | None
        duration_minutes: DF.Int
        end_date: DF.Date | None
        genre: DF.Link
        language: DF.Literal["English", "Hindi", "Gujarati", "Tamil", "Telugu", "Other"]
        movie_cast: DF.SmallText | None
        movie_status: DF.Literal["Upcoming", "Now Showing", "Ended"]
        naming_series: DF.Literal["MOV-.#####"]
        poster: DF.AttachImage | None
        rating: DF.Literal["U", "UA", "A", "S"]
        release_date: DF.Date
        slug: DF.Data | None
        synopsis: DF.TextEditor | None
        title: DF.Data
        trailer_url: DF.Data | None
    # end: auto-generated types

    def before_save(self):
        self.generate_slug()

    def validate(self):
        self.validate_duration()
        self.validate_dates()
        self.compute_movie_status()

    def generate_slug(self):
        """Auto-generate a unique, URL-safe slug from title.
        Only regenerates when the title has changed (or slug is empty),
        so a manually-adjusted slug on an existing record isn't silently
        overwritten on unrelated edits."""
        if not self.title:
            return

        if not self.is_new():
            old_title = frappe.db.get_value("Movie", self.name, "title")
            if old_title == self.title and self.slug:
                return

        base_slug = re.sub(r"[^a-z0-9]+", "-", self.title.strip().lower()).strip("-")

        slug = base_slug
        counter = 2
        while frappe.db.exists("Movie", {"slug": slug, "name": ["!=", self.name or ""]}):
            slug = f"{base_slug}-{counter}"
            counter += 1

        self.slug = slug

    def validate_duration(self):
        if self.duration_minutes is None:
            return
        if not (1 <= self.duration_minutes <= 600):
            frappe.throw(
                "Duration must be between 1 and 600 minutes.",
                title="Invalid Duration",
            )

    def validate_dates(self):
        if self.end_date and self.release_date:
            if getdate(self.end_date) <= getdate(self.release_date):
                frappe.throw(
                    "End Date must be after Release Date.",
                    title="Invalid Dates",
                )

    def compute_movie_status(self):
        if not self.release_date:
            return

        today = getdate()
        release_date = getdate(self.release_date)
        end_date = getdate(self.end_date) if self.end_date else None

        if today < release_date:
            self.movie_status = "Upcoming"
        elif end_date and today > end_date:
            self.movie_status = "Ended"
        else:
            self.movie_status = "Now Showing"