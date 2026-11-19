from kotr.catalog import Entry
from kotr.sidebar import entries

SIDEBAR = {
    "doctype": "Workspace Sidebar",
    "name": "Invoicing",
    "title": "Invoicing",
    "items": [{"label": "Home"}, {"label": "Chart of Accounts"}, {"label": " "}, {"icon": "x"}],
}
ICON = {"doctype": "Desktop Icon", "name": "Build", "label": "Build"}


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


def test_other_documents_are_ignored() -> None:
    assert entries([("x.json", {"doctype": "Workspace", "label": "Nope"}), ("y.json", [])]) == []


def test_app_aliases_cover_extra_source_roots() -> None:
    banking = Entry(msgid="Total Credit", locations=(("banking/src/Modal.tsx", 1),))
    assert banking.apps == frozenset({"erpnext"})
