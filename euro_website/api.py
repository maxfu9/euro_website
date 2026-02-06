import json
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
def get_checkout_profile():
    user = frappe.session.user
    if not user or user == "Guest":
        return {}

    customer = _get_customer_for_user(user)
    contact = _get_contact_for_user(user)
    address = _get_primary_address(customer)

    data = {}
    if contact:
        data["full_name"] = contact.get("first_name") or contact.get("name") or ""
        data["email"] = contact.get("email_id") or user
        data["phone"] = contact.get("phone") or ""
    else:
        data["full_name"] = ""
        data["email"] = user
        data["phone"] = ""

    if address:
        data.update(
            {
                "address_line1": address.get("address_line1") or "",
                "city": address.get("city") or "",
                "country": address.get("country") or "",
            }
        )

    return data


@frappe.whitelist()
def get_profile():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login required")
    contact = _get_contact_for_user(user)
    return {
        "full_name": contact.get("first_name") if contact else "",
        "email": contact.get("email_id") if contact else user,
        "phone": contact.get("phone") if contact else "",
    }


@frappe.whitelist()
def update_profile(full_name: str, email: str, phone: str = ""):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login required")
    _update_contact_for_user(user, full_name, email, phone)
    return {"ok": True}


@frappe.whitelist()
def list_addresses():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login required")
    customer = _get_customer_for_user(user)
    if not customer:
        return []
    addresses = frappe.get_all(
        "Address",
        filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", customer]],
        fields=["name", "address_title", "address_line1", "city", "country"],
        limit_page_length=50,
    )
    return addresses


@frappe.whitelist()
def save_address(address_name: str = None, address_title: str = None, address_line1: str = None, city: str = None, country: str = None):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login required")
    customer = _get_customer_for_user(user)
    if not customer:
        frappe.throw("Customer not found")
    if not address_title or not address_line1 or not city or not country:
        frappe.throw("Missing required fields")

    if address_name:
        doc = frappe.get_doc("Address", address_name)
        doc.address_title = address_title
        doc.address_line1 = address_line1
        doc.city = city
        doc.country = country
        doc.flags.ignore_permissions = True
        doc.save()
        return {"ok": True, "name": doc.name}

    doc = frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": address_title,
            "address_type": "Shipping",
            "address_line1": address_line1,
            "city": city,
            "country": country,
            "links": [{"link_doctype": "Customer", "link_name": customer}],
        }
    )
    doc.flags.ignore_permissions = True
    doc.insert()
    return {"ok": True, "name": doc.name}


@frappe.whitelist()
def delete_address(address_name: str):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Login required")
    if not address_name:
        frappe.throw("Missing address")
    doc = frappe.get_doc("Address", address_name)
    doc.flags.ignore_permissions = True
    doc.delete()
    return {"ok": True}


@frappe.whitelist(allow_guest=True)
def place_order(
    full_name: str,
    email: str,
    phone: str,
    address_line1: str,
    city: str,
    country: str,
    items,
    notes: str = "",
    payment_method: str = "Cash",
    update_profile: int = 0,
    update_address: int = 0,
):
    if not (full_name and email and address_line1 and city and country):
        frappe.throw("Missing required fields")

    if isinstance(items, str):
        items = json.loads(items)
    if not items:
        frappe.throw("Cart is empty")

    from euro_website.handlers import _get_group_and_price, _get_or_create_customer, _ensure_contact

    customer_group, price_list, customer_type_value = _get_group_and_price("Retail")
    customer = _get_or_create_customer(full_name, email, customer_type="Retail")
    _ensure_contact(customer, full_name, email)

    address_name = _create_or_update_address(
        full_name,
        address_line1,
        city,
        country,
        customer,
        update_address=bool(int(update_address)),
    )

    company = frappe.defaults.get_global_default("company")
    if not company:
        company = frappe.get_all("Company", fields=["name"], limit_page_length=1)[0].name

    so_items = []
    for item in items:
        if not item.get("item_code"):
            continue
        warehouse = _get_item_warehouse(item.get("item_code"), company)
        so_items.append(
            {
                "item_code": item.get("item_code"),
                "qty": item.get("qty") or 1,
                "rate": item.get("rate") or 0,
                "price_list_rate": item.get("rate") or 0,
                "warehouse": warehouse,
            }
        )

    if not so_items:
        frappe.throw("Invalid cart items")

    payment_terms = _get_payment_terms(payment_method)
    remarks = notes or ""
    if payment_method:
        remarks = f"{remarks}\nPayment Method: {payment_method}".strip()

    so = frappe.get_doc(
        {
            "doctype": "Sales Order",
            "customer": customer,
            "customer_name": full_name,
            "transaction_date": frappe.utils.nowdate(),
            "delivery_date": frappe.utils.nowdate(),
            "order_type": "Sales",
            "company": company,
            "contact_email": email,
            "contact_phone": phone,
            "selling_price_list": price_list,
            "customer_group": customer_group,
            "is_webshop": 1,
            "shipping_address_name": address_name,
            "customer_address": address_name,
            "items": so_items,
            "remarks": remarks,
            "payment_terms_template": payment_terms,
        }
    )
    so.flags.ignore_permissions = True
    so.insert()

    submitted = False
    submit_error = None
    try:
        so.flags.ignore_permissions = True
        so.submit()
        submitted = True
    except Exception as exc:
        submit_error = str(exc)

    if frappe.session.user != "Guest" and bool(int(update_profile)):
        try:
            _update_contact_for_user(frappe.session.user, full_name, email, phone)
        except Exception:
            pass

    return {
        "ok": True,
        "sales_order": so.name,
        "submitted": submitted,
        "warning": submit_error,
    }


def _create_address(full_name, address_line1, city, country, customer):
    address = frappe.get_doc(
        {
            "doctype": "Address",
            "address_title": full_name,
            "address_type": "Shipping",
            "address_line1": address_line1,
            "city": city,
            "country": country,
            "links": [{"link_doctype": "Customer", "link_name": customer}],
        }
    )
    address.flags.ignore_permissions = True
    address.insert()
    return address.name


def _create_or_update_address(full_name, address_line1, city, country, customer, update_address=False):
    if update_address:
        existing = _get_primary_address(customer)
        if existing:
            doc = frappe.get_doc("Address", existing.name)
            doc.address_title = full_name
            doc.address_line1 = address_line1
            doc.city = city
            doc.country = country
            doc.flags.ignore_permissions = True
            doc.save()
            return doc.name
    return _create_address(full_name, address_line1, city, country, customer)


def _get_item_warehouse(item_code, company):
    warehouse = _get_value_if_field("Item", item_code, "default_warehouse")
    if warehouse:
        if _warehouse_belongs_to_company(warehouse, company):
            return warehouse

    if frappe.db.exists("DocType", "Item Default"):
        defaults = frappe.get_all(
            "Item Default",
            filters={"parent": item_code},
            fields=["default_warehouse"],
            limit_page_length=1,
        )
        if defaults and defaults[0].default_warehouse:
            if _warehouse_belongs_to_company(defaults[0].default_warehouse, company):
                return defaults[0].default_warehouse

    if company:
        warehouse = _get_value_if_field("Company", company, "default_warehouse")
        if warehouse and _warehouse_belongs_to_company(warehouse, company):
            return warehouse

    stock_settings = frappe.get_single("Stock Settings")
    warehouse = getattr(stock_settings, "default_warehouse", None) if stock_settings else None
    if warehouse and _warehouse_belongs_to_company(warehouse, company):
        return warehouse

    fallback = frappe.get_all(
        "Warehouse",
        filters={"company": company} if company else None,
        fields=["name"],
        limit_page_length=1,
    )
    if fallback:
        return fallback[0].name
    fallback_any = frappe.get_all("Warehouse", fields=["name"], limit_page_length=1)
    return fallback_any[0].name if fallback_any else None


def _get_value_if_field(doctype, name, fieldname):
    meta = frappe.get_meta(doctype)
    fieldnames = [df.fieldname for df in meta.fields if df.fieldname]
    if fieldname not in fieldnames:
        return None
    return frappe.db.get_value(doctype, name, fieldname)


def _warehouse_belongs_to_company(warehouse, company):
    if not warehouse or not company:
        return True
    wh_company = frappe.db.get_value("Warehouse", warehouse, "company")
    return not wh_company or wh_company == company


def _get_payment_terms(payment_method):
    if not payment_method:
        return None
    candidates = [payment_method, "Cash on Delivery", "Cash"]
    for name in candidates:
        if frappe.db.exists("Payment Terms Template", name):
            return name
    return None


def _get_customer_for_user(user):
    customer = frappe.get_all(
        "Customer",
        filters={"email_id": user},
        fields=["name"],
        limit_page_length=1,
    )
    if customer:
        return customer[0].name

    contact = _get_contact_for_user(user)
    if contact:
        link = frappe.get_all(
            "Dynamic Link",
            filters={"parent": contact.get("name"), "link_doctype": "Customer"},
            fields=["link_name"],
            limit_page_length=1,
        )
        if link:
            return link[0].link_name
    return None


def _get_contact_for_user(user):
    contact = frappe.get_all(
        "Contact",
        filters={"email_id": user},
        fields=["name", "first_name", "email_id", "phone"],
        limit_page_length=1,
    )
    return contact[0] if contact else None


def _get_primary_address(customer):
    if not customer:
        return None
    address = frappe.get_all(
        "Address",
        filters=[["Dynamic Link", "link_doctype", "=", "Customer"], ["Dynamic Link", "link_name", "=", customer]],
        fields=["name", "address_line1", "city", "country"],
        limit_page_length=1,
    )
    return address[0] if address else None


def _update_contact_for_user(user, full_name, email, phone):
    contact = _get_contact_for_user(user)
    if not contact:
        return
    doc = frappe.get_doc("Contact", contact.get("name"))
    doc.first_name = full_name
    doc.email_id = email
    doc.phone = phone
    doc.flags.ignore_permissions = True
    doc.save()

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
