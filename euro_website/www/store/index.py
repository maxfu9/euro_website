import frappe


def get_context(context):
    context.no_cache = 1
    context.title = "Store"
    filters = _get_filters()
    context.filters = filters
    page, page_size = _get_paging()
    context.page = page
    context.page_size = page_size
    context.categories = _get_categories()
    products, total = _get_products(filters, page, page_size)
    context.products = products
    context.total_products = total
    context.total_pages = max(1, (total + page_size - 1) // page_size)
    context.cart = _get_cart_summary()


def _get_filters():
    form = frappe.form_dict
    return {
        "q": (form.get("q") or "").strip(),
        "category": (form.get("category") or "").strip(),
        "min_price": _to_float(form.get("min_price")),
        "max_price": _to_float(form.get("max_price")),
    }


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get_paging():
    form = frappe.form_dict
    try:
        page = max(1, int(form.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = max(12, min(48, int(form.get("page_size", 24))))
    except (TypeError, ValueError):
        page_size = 24
    return page, page_size


def _get_products(filters, page, page_size):
    data_filters = {"published": 1}
    if filters.get("min_price") is not None and filters.get("max_price") is not None:
        data_filters["standard_rate"] = ["between", [filters.get("min_price") or 0, filters["max_price"]]]
    elif filters.get("min_price") is not None:
        data_filters["standard_rate"] = [">=", filters["min_price"]]
    elif filters.get("max_price") is not None:
        data_filters["standard_rate"] = ["<=", filters["max_price"]]

    or_filters = []
    if filters.get("q"):
        q = f"%{filters['q']}%"
        or_filters = [
            ["item_name", "like", q],
            ["website_description", "like", q],
            ["web_long_description", "like", q],
        ]

    if filters.get("category"):
        item_codes = _get_item_codes_by_category(filters["category"])
        if not item_codes:
            return [], 0
        data_filters["item_code"] = ["in", item_codes]

    fields = _available_fields(
        "Website Item",
        [
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
    items = frappe.get_all(
        "Website Item",
        filters=data_filters,
        or_filters=or_filters,
        fields=fields,
        order_by="modified desc",
        limit_start=(page - 1) * page_size,
        limit_page_length=page_size,
    )
    if or_filters:
        total = len(
            frappe.get_all(
                "Website Item",
                filters=data_filters,
                or_filters=or_filters,
                fields=["name"],
            )
        )
    else:
        total = frappe.db.count("Website Item", filters=data_filters)
    return items, total


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


def _get_categories():
    records = frappe.get_all(
        "Item",
        filters={"published_in_website": 1},
        fields=["item_group"],
        limit_page_length=500,
    )
    return sorted({row.item_group for row in records if row.item_group})


def _get_item_codes_by_category(category):
    records = frappe.get_all(
        "Item",
        filters={"published_in_website": 1, "item_group": category},
        fields=["item_code"],
        limit_page_length=1000,
    )
    return [row.item_code for row in records if row.item_code]


def _available_fields(doctype, candidates):
    meta = frappe.get_meta(doctype)
    if hasattr(meta, "get_fieldnames"):
        fieldnames = meta.get_fieldnames()
    else:
        fieldnames = [df.fieldname for df in meta.fields if df.fieldname]
    allowed = set(fieldnames + ["name", "owner", "creation", "modified", "modified_by"])
    return [field for field in candidates if field in allowed]


def _get_cart_summary():
    try:
        from erpnext.shopping_cart.cart import get_cart_quotation

        quotation = get_cart_quotation()
        return {
            "items": quotation.get("items", []),
            "grand_total": quotation.get("grand_total") or 0,
        }
    except Exception:
        return {"items": [], "grand_total": 0}
