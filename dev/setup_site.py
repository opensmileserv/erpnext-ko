import sys

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

KOREA = {
    "language": "한국어",
    "country": "Korea, Republic of",
    "timezone": "Asia/Seoul",
    "currency": "KRW",
    "company_name": "시범 회사",
    "company_abbr": "SB",
    "chart_of_accounts": "Standard",
    "fy_start_date": "2026-01-01",
    "fy_end_date": "2026-12-31",
    "setup_demo": 0,
}


def main(site: str) -> None:
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    try:
        if not frappe.is_setup_complete():
            setup_complete(KOREA)
        frappe.db.set_value("User", "Administrator", "language", "ko")
        frappe.db.commit()
        language = frappe.db.get_single_value("System Settings", "language")
        sys.stdout.write(f"{site}: 설정 완료, 시스템 언어 {language}\n")
    finally:
        frappe.destroy()


if __name__ == "__main__":
    main(sys.argv[1])
