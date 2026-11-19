from typing import TYPE_CHECKING, cast

from kotr.catalog import Entry, union

if TYPE_CHECKING:
    from collections.abc import Iterable

LINE = 1


def labels(document: object) -> list[tuple[str, str]]:
    if not isinstance(document, dict):
        return []
    fields = cast("dict[str, object]", document)
    doctype = fields.get("doctype")
    name = fields.get("name")
    found: list[tuple[str, str]] = []
    if doctype == "Workspace Sidebar":
        title = fields.get("title")
        if isinstance(title, str):
            found.append((title, f"Title of the Workspace Sidebar '{name}'"))
        items = fields.get("items")
        for item in cast("list[object]", items) if isinstance(items, list) else []:
            if isinstance(item, dict):
                label = cast("dict[str, object]", item).get("label")
                if isinstance(label, str):
                    found.append((label, f"Item label in the Workspace Sidebar '{name}'"))
    elif doctype == "Desktop Icon":
        label = fields.get("label")
        if isinstance(label, str):
            found.append((label, f"Label of the Desktop Icon '{name}'"))
    return [(text.strip(), note) for text, note in found if text.strip()]


def entries(documents: Iterable[tuple[str, object]]) -> list[Entry]:
    found = [
        Entry(msgid=text, locations=((path, LINE),), notes=(note,))
        for path, document in documents
        for text, note in labels(document)
    ]
    return union([found])
