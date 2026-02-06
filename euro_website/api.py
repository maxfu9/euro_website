import frappe


@frappe.whitelist(allow_guest=True)
def submit_contact(full_name: str, email: str, message: str):
    if not (full_name and email and message):
        frappe.throw("Missing required fields")

    lead = frappe.get_doc(
        {
            "doctype": "Lead",
            "lead_name": full_name,
            "email_id": email,
            "notes": message,
        }
    )
    lead.flags.ignore_permissions = True
    lead.insert()

    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def update_cart(item_code: str, qty: int = 1):
    if not item_code:
        frappe.throw("Missing item_code")

    updater = None
    try:
        from webshop.webshop.shopping_cart.cart import update_cart as updater
    except Exception:
        try:
            from erpnext.shopping_cart.cart import update_cart as updater
        except Exception:
            updater = None

    if not updater:
        frappe.throw("Shopping cart module not available")

    return updater(item_code=item_code, qty=qty)

@frappe.whitelist(allow_guest=True)
def signup_portal_user(full_name: str, email: str, password: str, is_trader: int = 0):
    if not (full_name and email and password):
        frappe.throw("Missing required fields")

    if frappe.db.exists("User", email):
        frappe.throw("Account already exists")

    customer_type = "Wholesale" if int(is_trader) else "Retail"
    customer = _create_customer_for_signup(full_name, email, customer_type)

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": full_name,
            "user_type": "Website User",
            "send_welcome_email": 0,
            "enabled": 1,
            "new_password": password,
        }
    )
    user.flags.ignore_permissions = True
    user.insert()

    if frappe.db.exists("Role", "Customer"):
        user.add_roles("Customer")

    return {"ok": True, "customer": customer}


def _create_customer_for_signup(full_name, email, customer_type):
    from euro_website.handlers import _get_group_and_price, _ensure_contact

    approved = customer_type != "Wholesale"
    customer_group, price_list, customer_type_value = _get_group_and_price(
        customer_type if approved else "Retail"
    )

    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": full_name,
            "customer_type": customer_type_value,
            "customer_group": customer_group,
            "territory": "All Territories",
            "email_id": email,
            "default_price_list": price_list,
        }
    )
    customer.flags.ignore_permissions = True
    customer.insert()

    _ensure_contact(customer.name, full_name, email)
    if customer_type == "Wholesale":
        _flag_wholesale_pending(customer.name, full_name, email)
    return customer.name


def _flag_wholesale_pending(customer_name, full_name, email):
    tag = "Wholesale Pending"
    try:
        frappe.add_tag(tag, "Customer", customer_name)
    except Exception:
        pass

    todo = frappe.get_doc(
        {
            "doctype": "ToDo",
            "description": f"Wholesale signup approval needed for {full_name} ({email})",
            "allocated_to": "Administrator",
            "reference_type": "Customer",
            "reference_name": customer_name,
        }
    )
    todo.flags.ignore_permissions = True
    todo.insert()
