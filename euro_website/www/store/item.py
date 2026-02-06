import frappe


def get_context(context):
    route = frappe.form_dict.get("item")
    if not route:
        frappe.throw("Not Found", frappe.DoesNotExistError)

    item = _get_item_by_route(route)
    if not item:
        frappe.throw("Not Found", frappe.DoesNotExistError)

    context.no_cache = 1
    context.title = item.item_name
    context.item = item
    context.gallery = _get_gallery(item)
    context.specs = _get_specs(item)
    context.highlights = _get_highlights(context.specs)
    context.reviews = _get_reviews(item)
    price_list = _get_price_list()
    context.price_list = price_list
    context.price = _get_item_price(item.item_code, price_list) or getattr(item, "standard_rate", 0) or 0


def _get_item_by_route(route):
    fields = _available_fields(
        "Website Item",
        [
            "name",
            "item_code",
            "item_name",
            "route",
            "thumbnail",
            "website_image",
            "website_description",
            "web_long_description",
            "description",
            "standard_rate",
        ],
    )
    records = frappe.get_all(
        "Website Item",
        filters={"route": route, "published": 1},
        fields=fields,
        limit_page_length=1,
    )
    if not records:
        # Fall back to item_code if route is not set
        records = frappe.get_all(
            "Website Item",
            filters={"item_code": route, "published": 1},
            fields=fields,
            limit_page_length=1,
        )

    if not records:
        return None

    return frappe.get_doc("Website Item", records[0].name)


def _get_gallery(item):
    images = []
    for field in ("website_image", "thumbnail", "image"):
        value = getattr(item, field, None)
        if value:
            images.append(value)

    if hasattr(item, "images"):
        for row in item.images:
            if getattr(row, "image", None):
                images.append(row.image)

    # de-duplicate while keeping order
    seen = set()
    unique = []
    for img in images:
        if img not in seen:
            unique.append(img)
            seen.add(img)
    return unique


def _get_specs(item):
    specs = []
    if hasattr(item, "website_specifications"):
        for row in item.website_specifications:
            label = getattr(row, "label", None) or getattr(row, "specification", None)
            value = getattr(row, "description", None) or getattr(row, "value", None)
            if label or value:
                specs.append({"label": label or "Detail", "value": value or ""})
    return specs


def _get_reviews(item):
    try:
        if not frappe.db.exists("DocType", "Item Review"):
            return []
        return frappe.get_all(
            "Item Review",
            filters={"item_code": item.item_code},
            fields=["customer_name", "rating", "review", "creation"],
            order_by="creation desc",
            limit_page_length=6,
        )
    except Exception:
        return []


def _get_highlights(specs):
    spec_map = {}
    for spec in specs or []:
        label = (spec.get("label") or "").strip().lower()
        if not label:
            continue
        normalized = _normalize_label(label)
        spec_map[normalized] = spec.get("value") or ""

    def pick(keys, fallback):
        for key in keys:
            value = spec_map.get(_normalize_label(key))
            if value:
                return value
        return fallback

    return [
        {
            "label": "Materials",
            "value": pick(["material", "materials", "plastic type"], "Varies by product"),
        },
        {
            "label": "Capacity",
            "value": pick(["capacity", "volume", "size"], "See specifications"),
        },
        {
            "label": "Food-safe",
            "value": pick(["food safe", "food-safe"], "Available on request"),
        },
        {
            "label": "BPA-free",
            "value": pick(["bpa free", "bpa-free"], "Available on request"),
        },
        {
            "label": "Dishwasher-safe",
            "value": pick(["dishwasher safe", "dishwasher-safe"], "Available on request"),
        },
    ]


def _normalize_label(label):
    return "".join(ch for ch in label.lower() if ch.isalnum())


def _available_fields(doctype, candidates):
    meta = frappe.get_meta(doctype)
    if hasattr(meta, "get_fieldnames"):
        fieldnames = meta.get_fieldnames()
    else:
        fieldnames = [df.fieldname for df in meta.fields if df.fieldname]
    allowed = set(fieldnames + ["name", "owner", "creation", "modified", "modified_by"])
    return [field for field in candidates if field in allowed]


def _get_price_list():
    user = frappe.session.user
    if user and user != "Guest":
        customer = _get_customer_for_user(user)
        if customer:
            group = frappe.db.get_value("Customer", customer, "customer_group")
            if group == "Commercial" and frappe.db.exists("Price List", "Standard Selling"):
                return "Standard Selling"
    if frappe.db.exists("Price List", "Website Price List"):
        return "Website Price List"
    if frappe.db.exists("Price List", "Standard Selling"):
        return "Standard Selling"
    price_list = frappe.get_all("Price List", filters={"selling": 1}, fields=["name"], limit_page_length=1)
    return price_list[0].name if price_list else None


def _get_item_price(item_code, price_list):
    if not item_code or not price_list:
        return None
    price = frappe.db.get_value(
        "Item Price",
        {"item_code": item_code, "price_list": price_list, "selling": 1},
        "price_list_rate",
    )
    return price


def _get_customer_for_user(user):
    customer = frappe.get_all(
        "Customer",
        filters={"email_id": user},
        fields=["name"],
        limit_page_length=1,
    )
    if customer:
        return customer[0].name

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
            return link[0].link_name
    return None
