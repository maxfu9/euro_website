import frappe


def get_context(context):
    context.no_cache = 1
    context.summary = {
        "order_total": 0,
        "invoice_total": 0,
        "outstanding_total": 0,
        "payments_total": 0,
    }

    if frappe.session.user == "Guest":
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = "/login?redirect-to=/portal"
        return

    customer = _get_customer_for_user(frappe.session.user)
    context.customer = customer
    context.pending_trader = _is_wholesale_pending(customer)
    context.orders = _get_orders(customer)
    context.invoices = _get_invoices(customer)
    context.payments = _get_payments(customer)
    context.summary = _build_summary(context.orders, context.invoices, context.payments)


def _get_customer_for_user(user):
    customer = frappe.get_all(
        "Customer",
        filters={"email_id": user},
        fields=["name", "customer_name"],
        limit_page_length=1,
    )
    if customer:
        return customer[0]

    contact = frappe.get_all(
        "Contact",
        filters={"email_id": user},
        fields=["name"],
        limit_page_length=1,
    )
    if contact:
        link = frappe.get_all(
            "Dynamic Link",
            filters={"parent": contact[0].name, "link_doctype": "Customer"},
            fields=["link_name"],
            limit_page_length=1,
        )
        if link:
            return {"name": link[0].link_name, "customer_name": link[0].link_name}

    return None


def _is_wholesale_pending(customer):
    if not customer:
        return False
    return frappe.db.exists(
        "Tag Link",
        {
            "document_type": "Customer",
            "document_name": customer["name"],
            "tag": "Wholesale Pending",
        },
    )


def _get_orders(customer):
    if not customer:
        return []
    return frappe.get_all(
        "Sales Order",
        filters={"customer": customer["name"]},
        fields=["name", "transaction_date", "status", "grand_total"],
        order_by="transaction_date desc",
        limit_page_length=20,
    )


def _get_invoices(customer):
    if not customer:
        return []
    return frappe.get_all(
        "Sales Invoice",
        filters={"customer": customer["name"]},
        fields=["name", "posting_date", "status", "grand_total", "outstanding_amount"],
        order_by="posting_date desc",
        limit_page_length=20,
    )


def _get_payments(customer):
    if not customer:
        return []
    return frappe.get_all(
        "Payment Entry",
        filters={"party_type": "Customer", "party": customer["name"]},
        fields=["name", "posting_date", "status", "paid_amount", "paid_to_account_currency"],
        order_by="posting_date desc",
        limit_page_length=20,
    )


def _build_summary(orders, invoices, payments):
    order_total = sum(order.grand_total or 0 for order in orders)
    invoice_total = sum(invoice.grand_total or 0 for invoice in invoices)
    outstanding_total = sum(invoice.outstanding_amount or 0 for invoice in invoices)
    payments_total = sum(payment.paid_amount or 0 for payment in payments)
    return {
        "order_total": order_total,
        "invoice_total": invoice_total,
        "outstanding_total": outstanding_total,
        "payments_total": payments_total,
    }
