import json
from typing import TYPE_CHECKING

from kotr.catalog import Entry
from kotr.desk import entries, load_documents

if TYPE_CHECKING:
    from pathlib import Path

SIDEBAR = {
    "doctype": "Workspace Sidebar",
    "name": "Invoicing",
    "title": "Invoicing",
    "items": [{"label": "Home"}, {"label": "Chart of Accounts"}, {"label": " "}, {"icon": "x"}],
}
ICON = {"doctype": "Desktop Icon", "name": "Build", "label": "Build"}
EMPTY = "Your income and expenses over the year, and what's left as profit."
CHART = {
    "doctype": "Dashboard Chart",
    "name": "Profit and Loss",
    "chart_name": "Profit and Loss",
    "empty_state_message": EMPTY,
}
CARD = {"doctype": "Number Card", "name": "Sales Orders Count", "label": "Sales Orders Count"}


def test_sidebar_titles_items_and_icons_become_messages() -> None:
    found = entries(
        [
            ("erpnext/erpnext/workspace_sidebar/invoicing.json", SIDEBAR),
            ("frappe/frappe/desktop_icon/build.json", ICON),
            ("frappe/frappe/desktop_icon/other.json", {"doctype": "Desktop Icon", "label": "Home"}),
        ]
    )
    by_id = {entry.msgid: entry for entry in found}
    assert sorted(by_id) == ["Build", "Chart of Accounts", "Home", "Invoicing"]
    assert by_id["Home"].apps == frozenset({"erpnext", "frappe"})
    assert by_id["Chart of Accounts"].notes == ("Item label in the Workspace Sidebar 'Invoicing'",)


def test_dashboard_charts_and_number_cards_become_messages() -> None:
    found = entries(
        [
            (
                "erpnext/erpnext/accounts/dashboard_chart/profit_and_loss/profit_and_loss.json",
                CHART,
            ),
            (
                "erpnext/erpnext/selling/number_card/sales_orders_count/sales_orders_count.json",
                CARD,
            ),
        ]
    )
    by_id = {entry.msgid: entry for entry in found}
    assert sorted(by_id) == ["Profit and Loss", "Sales Orders Count", EMPTY]
    assert by_id[EMPTY].notes == ("Empty state message of the Dashboard Chart 'Profit and Loss'",)
    assert by_id["Sales Orders Count"].apps == frozenset({"erpnext"})


def test_documents_are_found_at_app_and_module_level(tmp_path: Path) -> None:
    layout = {
        "frappe/frappe/desktop_icon/build.json": ICON,
        "erpnext/erpnext/workspace_sidebar/invoicing.json": SIDEBAR,
        "erpnext/erpnext/accounts/dashboard_chart/profit_and_loss/profit_and_loss.json": CHART,
        "erpnext/erpnext/selling/number_card/sales_orders_count/sales_orders_count.json": CARD,
        "erpnext/erpnext/accounts/doctype/account/account.json": {"doctype": "DocType"},
    }
    for path, document in layout.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(document), encoding="utf-8")
    found = sorted(path for path, _ in load_documents(tmp_path))
    assert found == sorted(path for path in layout if "/doctype/" not in path)


def test_other_documents_are_ignored() -> None:
    assert entries([("x.json", {"doctype": "Workspace", "label": "Nope"}), ("y.json", [])]) == []


def test_app_aliases_cover_extra_source_roots() -> None:
    banking = Entry(msgid="Total Credit", locations=(("banking/src/Modal.tsx", 1),))
    assert banking.apps == frozenset({"erpnext"})
