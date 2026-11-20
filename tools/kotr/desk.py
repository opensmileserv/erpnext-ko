import json
from typing import TYPE_CHECKING, cast

from kotr.catalog import Entry, union

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

LINE = 1
PATTERNS = (
    "*/*/workspace_sidebar/*.json",
    "*/*/desktop_icon/*.json",
    "*/*/*/dashboard_chart/*/*.json",
    "*/*/*/number_card/*/*.json",
)
FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "Desktop Icon": (("label", "Label of the Desktop Icon"),),
    "Dashboard Chart": (
        ("chart_name", "Name of the Dashboard Chart"),
        ("empty_state_message", "Empty state message of the Dashboard Chart"),
    ),
    "Number Card": (("label", "Label of the Number Card"),),
}


def load_documents(source: Path) -> list[tuple[str, object]]:
    return [
        (path.relative_to(source).as_posix(), json.loads(path.read_text(encoding="utf-8")))
        for pattern in PATTERNS
        for path in sorted(source.glob(pattern))
    ]


def sidebar_labels(fields: dict[str, object]) -> list[tuple[str, str]]:
    name = fields.get("name")
    found: list[tuple[str, str]] = []
    title = fields.get("title")
    if isinstance(title, str):
        found.append((title, f"Title of the Workspace Sidebar '{name}'"))
    items = fields.get("items")
    for item in cast("list[object]", items) if isinstance(items, list) else []:
        if isinstance(item, dict):
            label = cast("dict[str, object]", item).get("label")
            if isinstance(label, str):
                found.append((label, f"Item label in the Workspace Sidebar '{name}'"))
    return found


def labels(document: object) -> list[tuple[str, str]]:
    if not isinstance(document, dict):
        return []
    fields = cast("dict[str, object]", document)
    doctype = fields.get("doctype")
    if not isinstance(doctype, str):
        return []
    found = sidebar_labels(fields) if doctype == "Workspace Sidebar" else []
    name = fields.get("name")
    for key, note in FIELDS.get(doctype, ()):
        value = fields.get(key)
        if isinstance(value, str):
            found.append((value, f"{note} '{name}'"))
    return [(text.strip(), note) for text, note in found if text.strip()]


def entries(documents: Iterable[tuple[str, object]]) -> list[Entry]:
    found = [
        Entry(msgid=text, locations=((path, LINE),), notes=(note,))
        for path, document in documents
        for text, note in labels(document)
    ]
    return union([found])
