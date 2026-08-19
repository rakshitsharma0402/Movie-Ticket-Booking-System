# Copyright (c) 2026, Rakshit Sharma and contributors
# For license information, please see license.txt

"""
override_whitelisted_methods concept demo.

WHAT THIS IS:
Frappe allows replacing the implementation of a whitelisted method
site-wide via the `override_whitelisted_methods` hook in hooks.py.
Any call to the original dotted path (e.g. "frappe.client.get_count",
whether from the Desk UI, REST API, or another app) is transparently
routed to the override instead. The override is responsible for
producing an equivalent result — here, by logging and then delegating
to the original implementation, so behavior is unchanged for callers.

USE CASES:
- Audit logging of sensitive/high-traffic whitelisted calls (as here).
- Adding caching or rate limiting in front of a hot, expensive
  whitelisted method without touching frappe core.
- Patching a bug or adjusting behavior in a whitelisted method from
  frappe core or another installed app, without forking that app.
- Enforcing extra business-rule validation on a generic method (e.g.
  blocking frappe.client.delete on certain doctypes) that the caller
  can't bypass by hitting the method directly.

RISKS:
- Silent behavior drift: if the original method's signature changes
  in a future Frappe version, this override can break or silently
  stop matching correctly, since it's not type-checked against the
  original at import time.
- Global blast radius: this override applies EVERYWHERE get_count is
  called — Desk list view counts, sidebar counts, any custom code
  calling get_count — not just movietickets' own doctypes. A bug here
  affects the whole site, not just this app.
- Debugging opacity: a stack trace inside an override can look like
  it's coming from frappe.client itself, confusing anyone who doesn't
  know an override is registered, unless logging like this makes the
  substitution obvious.
- Security: overrides run with the same permission context as the
  original call. It's easy to accidentally weaken a check (e.g. by
  forgetting a permission filter this override doesn't add back) while
  believing you've only added logging.

WHEN TO USE THIS VS. ALTERNATIVES:
- If you only need to observe a call (not change behavior), a
  `before_request` / `after_request` hook or Frappe's built-in request
  logging is usually a better, less invasive fit than overriding the
  method itself.
- If you need doctype-specific behavior (not "every call to
  get_count, for any doctype, sitewide"), a `has_permission` hook or a
  DocType-level `get_list`/`get_count` controller override is more
  targeted and less globally risky than this mechanism.
- override_whitelisted_methods is best reserved for cases that
  genuinely need to intercept a *generic*, cross-doctype API method
  itself — like this logging demo — not as a general-purpose place to
  put doctype-specific logic.
"""

import frappe
from frappe.client import get_count as _original_get_count


@frappe.whitelist()
def get_count_with_logging(doctype=None, filters=None, debug=False, cache=False):
	"""Logs the doctype and filters of every get_count call, then
	delegates to Frappe's original implementation so behavior for
	callers is unchanged."""
	frappe.logger("movietickets").info(
		f"[override_whitelisted_methods] get_count called: doctype={doctype!r}, filters={filters!r}"
	)

	return _original_get_count(doctype=doctype, filters=filters, debug=debug, cache=cache)