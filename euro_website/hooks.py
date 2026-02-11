app_name = "euro_website"
app_title = "Euro Website"
app_publisher = "Your Company"
app_description = "Custom ERPNext public website frontend"
app_email = "hello@example.com"
app_license = "MIT"

# Hide default Frappe navbar/footer across public website pages
def get_website_context(context):
    try:
        import frappe

        settings = frappe.get_cached_doc("Website Settings", "Website Settings")
        website_brand = settings.brand_image or getattr(settings, "banner_image", None)
        website_footer = (
            getattr(settings, "footer_logo", None)
            or getattr(settings, "logo", None)
            or settings.brand_image
            or getattr(settings, "banner_image", None)
        )

        company_logo = None
        try:
            default_company = frappe.db.get_single_value("Global Defaults", "default_company")
            if not default_company:
                default_company = frappe.db.get_value("Company", {"is_default": 1}, "name")
            if default_company:
                company_logo = frappe.db.get_value("Company", default_company, "company_logo")
        except Exception:
            company_logo = None

        context.brand_image = website_brand or company_logo
        context.nav_logo = context.brand_image
        context.footer_logo = (
            website_footer
            or website_brand
            or company_logo
        )
        context.base_template_path = "euro_website/templates/base_custom.html"
        context.meta_title = "Euro Plast"
        context.meta_description = (
            "Euro Plast manufactures homeware and kitchenware for retail and wholesale customers."
        )
        context.meta_image = context.brand_image
        path = frappe.request.path if getattr(frappe, "request", None) else "/"
        context.meta_url = frappe.utils.get_url(path)
        context.schema_json = frappe.as_json(
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Euro Plast",
                "url": frappe.utils.get_url(),
                "logo": context.brand_image or "",
            }
        )
    except Exception:
        context.brand_image = None

    context.hide_navbar = 1
    context.hide_footer = 1


website_context = {}

# Website assets
web_include_css = [
    "/assets/euro_website/css/euro_website.css",
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css",
]
web_include_js = [
    "/assets/euro_website/js/site.js",
    "/assets/euro_website/js/store.js",
]

website_route_rules = [
    {"from_route": "/store/<item>", "to_route": "store/item"},
    {"from_route": "/login", "to_route": "login"},
]

doc_events = {
    "Sales Order": {
        "before_insert": "euro_website.handlers.ensure_web_customer",
    }
}
