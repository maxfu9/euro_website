def get_context(context):
    import frappe

    context.no_cache = 1
    user = frappe.session.user
    if not user or user == "Guest":
        context.redirect_to = "/signup"
    else:
        user_type = frappe.db.get_value("User", user, "user_type") or "Website User"
        context.redirect_to = "/app" if user_type == "System User" else None

