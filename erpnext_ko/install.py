import frappe
from frappe.gettext.translate import compile_translations
from frappe.translate import clear_cache

APP = "erpnext_ko"
LOCALE = "ko"


def activate() -> None:
    frappe.db.set_value("Language", LOCALE, "enabled", 1)
    compile_translations(APP, LOCALE, force=True)
    clear_cache()
