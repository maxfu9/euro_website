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
    context.reviews = _get_reviews(item)


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


def _available_fields(doctype, candidates):
    meta = frappe.get_meta(doctype)
    allowed = set(meta.get_fieldnames() + ["name", "owner", "creation", "modified", "modified_by"])
    return [field for field in candidates if field in allowed]
