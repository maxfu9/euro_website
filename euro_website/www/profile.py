import frappe


def get_context(context):
    context.no_cache = 1
    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login?redirect-to=/profile"
        return
    context.title = "Profile"
