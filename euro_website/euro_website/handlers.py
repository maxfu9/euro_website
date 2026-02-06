import frappe


def ensure_web_customer(doc, method=None):
    # Only process web orders for guests or missing customer
    if doc.get("customer") and doc.customer != "Guest":
        if not doc.get("is_webshop"):
            return
        _ensure_user_for_customer(doc.customer, doc.get("contact_email") or doc.get("email_id"))
        return

    email = _get_email(doc)
    if not email:
        return

    customer_name = _get_customer_name(doc, email)
    customer = _get_or_create_customer(customer_name, email, customer_type="Retail")
    _ensure_contact(customer, customer_name, email)
    _link_addresses(customer, doc)
    _ensure_user_for_customer(customer, email)

    doc.customer = customer
    doc.customer_name = customer_name
    _apply_price_list(doc, customer_type="Retail")


def _get_email(doc):
    for key in ("contact_email", "email_id", "customer_email"):
        value = doc.get(key)
        if value:
            return value
    return None


def _get_customer_name(doc, email):
    for key in ("contact_display", "contact_person", "customer_name"):
        value = doc.get(key)
        if value:
            return value
    return email.split("@")[0].replace(".", " ").title()


def _get_or_create_customer(name, email, customer_type="Retail"):
    customer_group, price_list, customer_type_value = _get_group_and_price(customer_type)
    existing = frappe.get_all(
        "Customer",
        filters={"email_id": email},
        fields=["name"],
        limit_page_length=1,
    )
    if existing:
        return existing[0].name

    customer = frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": name,
            "customer_type": customer_type_value,
            "customer_group": customer_group,
            "territory": "All Territories",
            "email_id": email,
            "default_price_list": price_list,
        }
    )
    customer.flags.ignore_permissions = True
    customer.insert()
    return customer.name


def _ensure_contact(customer, name, email):
    contact = frappe.get_all(
        "Contact",
        filters={"email_id": email},
        fields=["name"],
        limit_page_length=1,
    )
    if contact:
        _link_contact_to_customer(contact[0].name, customer)
        return

    contact_doc = frappe.get_doc(
        {
            "doctype": "Contact",
            "first_name": name,
            "email_id": email,
            "links": [{"link_doctype": "Customer", "link_name": customer}],
        }
    )
    contact_doc.flags.ignore_permissions = True
    contact_doc.insert()


def _link_contact_to_customer(contact_name, customer):
    contact_doc = frappe.get_doc("Contact", contact_name)
    for link in contact_doc.links:
        if link.link_doctype == "Customer" and link.link_name == customer:
            return
    contact_doc.append("links", {"link_doctype": "Customer", "link_name": customer})
    contact_doc.flags.ignore_permissions = True
    contact_doc.save()


def _link_addresses(customer, doc):
    for field in ("shipping_address_name", "customer_address"):
        address_name = doc.get(field)
        if not address_name:
            continue
        try:
            address = frappe.get_doc("Address", address_name)
            if not any(link.link_doctype == "Customer" and link.link_name == customer for link in address.links):
                address.append("links", {"link_doctype": "Customer", "link_name": customer})
                address.flags.ignore_permissions = True
                address.save()
        except Exception:
            continue


def _ensure_user_for_customer(customer, email):
    if not email:
        return

    if frappe.db.exists("User", email):
        return

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": email.split("@")[0],
            "user_type": "Website User",
            "send_welcome_email": 1,
            "enabled": 1,
        }
    )
    user.flags.ignore_permissions = True
    user.insert()

    if frappe.db.exists("Role", "Customer"):
        user.add_roles("Customer")


def _apply_price_list(doc, customer_type="Retail"):
    customer_group, price_list, _ = _get_group_and_price(customer_type)
    if not doc.get("customer_group"):
        doc.customer_group = customer_group
    if not doc.get("selling_price_list"):
        doc.selling_price_list = price_list


def _get_group_and_price(customer_type):
    if customer_type == "Wholesale":
        customer_group = "Commercial"
        price_list = "Standard Selling"
        customer_type_value = "Company"
    else:
        customer_group = "Individual"
        price_list = "Website Price List"
        customer_type_value = "Individual"

    if not frappe.db.exists("Customer Group", customer_group):
        group = frappe.get_doc({"doctype": "Customer Group", "customer_group_name": customer_group})
        group.flags.ignore_permissions = True
        group.insert()

    if not frappe.db.exists("Price List", price_list):
        plist = frappe.get_doc(
            {"doctype": "Price List", "price_list_name": price_list, "selling": 1, "currency": frappe.defaults.get_global_default("currency") or "USD"}
        )
        plist.flags.ignore_permissions = True
        plist.insert()

    return customer_group, price_list, customer_type_value
