app_name = "euro_website"
app_title = "Euro Website"
app_publisher = "Your Company"
app_description = "Custom ERPNext public website frontend"
app_email = "hello@example.com"
app_license = "MIT"

# Website assets
web_include_css = [
    "/assets/euro_website/css/euro_website.css",
]
web_include_js = [
    "/assets/euro_website/js/site.js",
    "/assets/euro_website/js/store.js",
]

website_route_rules = [
    {"from_route": "/store/<item>", "to_route": "euro_website/store/item"},
]

doc_events = {
    "Sales Order": {
        "before_insert": "euro_website.handlers.ensure_web_customer",
    }
}
