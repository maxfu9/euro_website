import frappe


def get_context(context):
    context.no_cache = 1
    context.featured = _get_rotating_item()
    context.lineup = _get_lineup_items() or []
    context.featured_image = _get_featured_image(context.featured)


def _get_rotating_item():
    fields = _available_fields(
        "Website Item",
        [
            "item_code",
            "item_name",
            "web_item_name",
            "route",
            "thumbnail",
            "website_image",
            "website_description",
            "web_long_description",
            "description",
        ],
    )
    items = frappe.get_all(
        "Website Item",
        filters={"published": 1},
        fields=fields,
        limit_page_length=500,
    )
    if not items:
        return None

    item_groups = _get_item_groups(items)
    categories = sorted({group for group in item_groups.values() if group})
    if not categories:
        return _random_item(items)

    today = frappe.utils.now_datetime().date()
    category = categories[today.toordinal() % len(categories)]
    filtered = [item for item in items if item_groups.get(item.item_code) == category]
    return _random_item(filtered or items)


def _get_lineup_items():
    fields = _available_fields(
        "Website Item",
        [
            "item_code",
            "item_name",
            "web_item_name",
            "route",
            "thumbnail",
            "website_image",
            "website_description",
            "web_long_description",
            "description",
            "standard_rate",
        ],
    )
    return frappe.get_all(
        "Website Item",
        filters={"published": 1},
        fields=fields,
        order_by="modified desc",
        limit_page_length=4,
    )


def _get_featured_image(item):
    if not item:
        return "/assets/frappe/images/ui/placeholder-image.png"
    return item.get("thumbnail") or item.get("website_image") or "/assets/frappe/images/ui/placeholder-image.png"


def _random_item(items):
    if not items:
        return None
    import random

    return items[random.randint(0, len(items) - 1)]


def _get_item_groups(items):
    codes = [item.item_code for item in items if item.get("item_code")]
    if not codes:
        return {}

    records = frappe.get_all(
        "Item",
        filters={"item_code": ["in", codes]},
        fields=["item_code", "item_group"],
    )
    return {record.item_code: record.item_group for record in records}


def _available_fields(doctype, candidates):
    meta = frappe.get_meta(doctype)
    if hasattr(meta, "get_fieldnames"):
        fieldnames = meta.get_fieldnames()
    else:
        fieldnames = [df.fieldname for df in meta.fields if df.fieldname]
    allowed = set(fieldnames + ["name", "owner", "creation", "modified", "modified_by"])
    return [field for field in candidates if field in allowed]
