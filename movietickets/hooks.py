app_name = "movietickets"
app_title = "Movie Ticket Booking"
app_publisher = "Rakshit Sharma"
app_description = "Movies Tickt Booking System"
app_email = "sharma@gmail.com"
app_license = "mit"

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "movietickets",
# 		"logo": "/assets/movietickets/logo.png",
# 		"title": "Movie Ticket Booking",
# 		"route": "/movietickets",
# 		"has_permission": "movietickets.api.permission.has_app_permission",
# 	}
# ]

# Companion apps that extend a host app (instead of taking their own apps-screen icon) can pin
# their workspaces into the host app's workspace dock (rail) with this hook. Declaring it keeps
# the app off the apps screen, so it takes precedence over any add_to_apps_screen above. Who can
# see a pinned workspace is controlled by that workspace's own Roles table.
# add_to_workspace_dock = [
# 	{
# 		"app": "erpnext",
# 		"workspace": "My Workspace",
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/movietickets/css/movietickets.css"
# app_include_js = "/assets/movietickets/js/movietickets.js"

# include js, css files in header of web template
# web_include_css = "/assets/movietickets/css/movietickets.css"
# web_include_js = "/assets/movietickets/js/movietickets.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "movietickets/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "movietickets/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "movietickets.utils.jinja_methods",
# 	"filters": "movietickets.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "movietickets.install.before_install"
# after_install = "movietickets.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "movietickets.uninstall.before_uninstall"
# after_uninstall = "movietickets.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "movietickets.utils.before_app_install"
# after_app_install = "movietickets.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "movietickets.utils.before_app_uninstall"
# after_app_uninstall = "movietickets.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "movietickets.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "movietickets.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"movietickets.tasks.all"
# 	],
# 	"daily": [
# 		"movietickets.tasks.daily"
# 	],
# 	"hourly": [
# 		"movietickets.tasks.hourly"
# 	],
# 	"weekly": [
# 		"movietickets.tasks.weekly"
# 	],
# 	"monthly": [
# 		"movietickets.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "movietickets.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "movietickets.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "movietickets.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "movietickets.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["movietickets.utils.before_request"]
# after_request = ["movietickets.utils.after_request"]

# Job Events
# ----------
# before_job = ["movietickets.utils.before_job"]
# after_job = ["movietickets.utils.after_job"]

# after_file_upload = ["movietickets.utils.after_file_upload"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"movietickets.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

#fixtures

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["dt", "=", "Ticket Booking"]],
	},
	{
		"dt": "Property Setter",
		"filters": [["doc_type", "=", "Show"]],
	},
]

has_permission = {
	"Ticket Booking": "movietickets.movie_ticket_booking.doctype.ticket_booking.ticket_booking.has_permission",
}

scheduler_events = {
	"cron": {
		"*/5 * * * *": ["movietickets.tasks.expire_stale_bookings"],
		"0 23 * * *": ["movietickets.tasks.send_daily_revenue_digest"],
	},
	"daily": ["movietickets.tasks.update_movie_status"],
	"hourly": ["movietickets.tasks.update_show_status"],
}
  
doc_events = {
	"Ticket Booking": {
		"after_insert": "movietickets.notification_hooks.send_booking_received_email",
		"on_submit": "movietickets.notification_hooks.send_booking_confirmation_on_submit",
	},
	"Movie": {
		"before_save": "movietickets.notification_hooks.regenerate_movie_slug_and_status",
	},
}

override_whitelisted_methods = {
	"frappe.client.get_count": "movietickets.overrides.get_count_with_logging",