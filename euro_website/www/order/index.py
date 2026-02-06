import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "Order Confirmation"
    context.order_id = frappe.form_dict.get("order")
