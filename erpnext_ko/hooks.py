app_name = "erpnext_ko"
app_title = "ERPNext Ko"
app_publisher = "Smileserv"
app_description = "ERPNext·Frappe 한국어 번역"
app_email = ""
app_license = "gpl-3.0"

required_apps = ["frappe/erpnext"]

after_install = "erpnext_ko.install.activate"
after_migrate = "erpnext_ko.install.activate"
