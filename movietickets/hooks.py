app_name = "movietickets"
app_title = "Movie Ticket Booking"
app_publisher = "Rakshit Sharma"
app_description = "Movies Tickt Booking System"
app_email = "sharma@gmail.com"
app_license = "mit"

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# Includes in <head>
# ------------------

app_include_css = "/assets/movietickets/css/cinema.css"
app_include_js = "/assets/movietickets/js/cinema.js"

# Fixtures
# --------

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["dt", "=", "Ticket Booking"]],
	},
	{
		"dt": "Property Setter",
		"filters": [["doc_type", "=", "Show"]],
	},
    {
		"dt": "Custom DocPerm",
		"filters": [["role", "=", "Box Office Staff"], ["parent", "=", "Print Format"]],
	},

]

# Permissions
# -----------

has_permission = {
	"Ticket Booking": "movietickets.movie_ticket_booking.doctype.ticket_booking.ticket_booking.has_permission",
}

# Document Events
# ---------------

doc_events = {
	"Ticket Booking": {
		"after_insert": "movietickets.notification_hooks.send_booking_received_email",
		"on_submit": "movietickets.notification_hooks.send_booking_confirmation_on_submit",
	},
	"Movie": {
		"before_save": "movietickets.notification_hooks.regenerate_movie_slug_and_status",
	},
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"*/5 * * * *": ["movietickets.tasks.expire_stale_bookings"],
		"0 23 * * *": ["movietickets.tasks.send_daily_revenue_digest"],
	},
	"daily": ["movietickets.tasks.update_movie_status"],
	"hourly": ["movietickets.tasks.update_show_status"],
}

# Overriding Methods
# -------------------

override_whitelisted_methods = {
	"frappe.client.get_count": "movietickets.overrides.get_count_with_logging",
}