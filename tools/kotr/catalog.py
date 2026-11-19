import io
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from babel.messages.catalog import Catalog, Message
from babel.messages.mofile import write_mo
from babel.messages.pofile import read_po, write_po

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

MACHINE = "mt"
APP_OF_SEGMENT = {
    "frappe": "frappe",
    "ui": "frappe",
    "erpnext": "erpnext",
    "banking": "erpnext",
    "islands": "erpnext",
}
SKIP_PREFIX = "glossary-skip:"
HEADER_DATE = datetime(2026, 11, 19, tzinfo=UTC)
HEADER_COMMENT = "# ERPNext·Frappe 한국어 번역 (erpnext-ko)\n# GPL-3.0-or-later\n#"


type Location = tuple[str, int]
type Key = tuple[str, str | None]


class CatalogError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Entry:
    msgid: str
    context: str | None = None
    msgstr: str = ""
    flags: frozenset[str] = frozenset()
    locations: tuple[Location, ...] = ()
    notes: tuple[str, ...] = ()
    comments: tuple[str, ...] = ()

    @property
    def key(self) -> Key:
        return (self.msgid, self.context)

    @property
    def apps(self) -> frozenset[str]:
        segments = (path.split("/", 1)[0] for path, _ in self.locations)
        return frozenset(APP_OF_SEGMENT.get(segment, segment) for segment in segments)

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(path for path, _ in self.locations)

    @property
    def translated(self) -> bool:
        return bool(self.msgstr)

    @property
    def machine(self) -> bool:
        return MACHINE in self.flags

    @property
    def skips(self) -> frozenset[str]:
        return frozenset(
            comment.removeprefix(SKIP_PREFIX).strip().lower()
            for comment in self.comments
            if comment.startswith(SKIP_PREFIX)
        )


def plain(value: object, field: str) -> str:
    if isinstance(value, str):
        return value
    message = f"{field} 가 문자열이 아니다 (복수형 메시지는 다루지 않는다): {value!r}"
    raise CatalogError(message)


def entry_of(message: Message) -> Entry:
    return Entry(
        msgid=plain(message.id, "msgid"),
        context=message.context,
        msgstr=plain(message.string or "", "msgstr"),
        flags=frozenset(message.flags) - {"fuzzy"},
        locations=tuple(message.locations),
        notes=tuple(message.auto_comments),
        comments=tuple(message.user_comments),
    )


def message_of(entry: Entry) -> Message:
    return Message(
        entry.msgid,
        entry.msgstr,
        locations=entry.locations,
        flags=entry.flags,
        auto_comments=entry.notes,
        user_comments=entry.comments,
        context=entry.context,
    )


def parse(data: bytes) -> tuple[list[Entry], list[Entry]]:
    catalog = read_po(io.BytesIO(data), locale="ko")
    current = [entry_of(message) for message in catalog if message.id]
    obsolete = [entry_of(message) for message in catalog.obsolete.values() if message.id]
    return current, obsolete


def render(entries: Iterable[Entry], obsolete: Iterable[Entry] = ()) -> bytes:
    catalog = Catalog(
        header_comment=HEADER_COMMENT,
        locale="ko",
        domain="erpnext_ko",
        project="ERPNext Ko",
        version="16",
        copyright_holder="Smileserv",
        msgid_bugs_address="",
        creation_date=HEADER_DATE,
        revision_date=HEADER_DATE,
        last_translator="erpnext-ko",
        language_team="Korean",
        fuzzy=False,
    )
    for entry in entries:
        catalog[entry.msgid] = message_of(entry)
    for entry in obsolete:
        key = entry.msgid if entry.context is None else (entry.msgid, entry.context)
        catalog.obsolete[key] = message_of(entry)
    buffer = io.BytesIO()
    write_po(buffer, catalog, width=0)
    return buffer.getvalue()


def union(templates: Sequence[Sequence[Entry]]) -> list[Entry]:
    merged: dict[Key, Entry] = {}
    for template in templates:
        for entry in template:
            known = merged.get(entry.key)
            if known is None:
                merged[entry.key] = replace(entry, msgstr="", comments=())
                continue
            merged[entry.key] = replace(
                known,
                locations=tuple(dict.fromkeys(known.locations + entry.locations)),
                notes=tuple(dict.fromkeys(known.notes + entry.notes)),
                flags=known.flags | entry.flags,
            )
    return list(merged.values())


def merge(
    templates: Sequence[Sequence[Entry]], current: Sequence[Entry], obsolete: Sequence[Entry] = ()
) -> tuple[list[Entry], list[Entry]]:
    known = {entry.key: entry for entry in [*obsolete, *current]}
    merged: list[Entry] = []
    for entry in union(templates):
        previous = known.pop(entry.key, None)
        if previous is None:
            merged.append(entry)
            continue
        merged.append(
            replace(
                entry,
                msgstr=previous.msgstr,
                flags=entry.flags | (previous.flags & {MACHINE}),
                comments=previous.comments,
            )
        )
    retired = [entry for entry in known.values() if entry.translated]
    return merged, retired


def with_translation(entry: Entry, msgstr: str, *, machine: bool) -> Entry:
    flags = entry.flags | {MACHINE} if machine else entry.flags - {MACHINE}
    return replace(entry, msgstr=msgstr, flags=flags)


def compile_mo(entries: Iterable[Entry]) -> bytes:
    catalog = Catalog(locale="ko", domain="erpnext_ko")
    for entry in entries:
        if entry.translated:
            catalog[entry.msgid] = message_of(entry)
    buffer = io.BytesIO()
    write_mo(buffer, catalog)
    return buffer.getvalue()
