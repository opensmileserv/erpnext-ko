import json
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING, cast

from kotr.catalog import Entry

if TYPE_CHECKING:
    import re
    from collections.abc import Mapping, Sequence

    from kotr.glossary import Glossary, Term

HINT_LIMIT = 160

SYSTEM = files("kotr").joinpath("system.md").read_text(encoding="utf-8")


class ReplyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Request:
    entries: tuple[Entry, ...]
    system: str
    user: str


def pick(entries: Sequence[Entry], where: re.Pattern[str] | None, limit: int | None) -> list[Entry]:
    chosen = [
        entry
        for entry in entries
        if not entry.translated
        and entry.msgid.strip()
        and (where is None or any(where.search(path) for path in entry.paths))
    ]
    chosen.sort(key=lambda entry: (-len(entry.locations), len(entry.msgid), entry.msgid))
    return chosen if limit is None else chosen[:limit]


def batches(entries: Sequence[Entry], max_chars: int, max_items: int) -> list[list[Entry]]:
    groups: list[list[Entry]] = []
    current: list[Entry] = []
    size = 0
    for entry in entries:
        cost = len(entry.msgid) + len(hint(entry))
        if current and (size + cost > max_chars or len(current) >= max_items):
            groups.append(current)
            current, size = [], 0
        current.append(entry)
        size += cost
    if current:
        groups.append(current)
    return groups


def hint(entry: Entry) -> str:
    if entry.notes:
        return " ".join(entry.notes)[:HINT_LIMIT]
    if entry.paths:
        return entry.paths[0][:HINT_LIMIT]
    return ""


def glossary_lines(terms: Sequence[Term]) -> list[str]:
    lines: list[str] = []
    for term in terms:
        line = f"- {term.en} → {term.preferred}"
        if term.avoid:
            line += f" (피할 말: {', '.join(term.avoid)})"
        if term.note:
            line += f" — {term.note}"
        lines.append(line)
    return lines


def build(
    entries: Sequence[Entry],
    glossary: Glossary,
    feedback: Mapping[int, Sequence[str]] | None = None,
) -> Request:
    items: list[dict[str, object]] = []
    for number, entry in enumerate(entries):
        item: dict[str, object] = {"id": number, "en": entry.msgid, "where": hint(entry)}
        if entry.context:
            item["context"] = entry.context
        if feedback and number in feedback:
            item["fix"] = list(feedback[number])
        items.append(item)
    terms = glossary.relevant((entry.msgid, entry.apps) for entry in entries)
    parts = ["다음 문구들을 한국어로 옮겨라."]
    if terms:
        parts += ["", "용어집:", *glossary_lines(terms)]
    if feedback:
        parts += ["", "fix 가 있는 항목은 앞선 번역이 그 이유로 거절되었다. 고쳐서 다시 옮겨라."]
    parts += ["", "문구 (JSON):", json.dumps(items, ensure_ascii=False, indent=1)]
    return Request(tuple(entries), SYSTEM, "\n".join(parts))


def schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "ko": {"type": "string"}},
                    "required": ["id", "ko"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }


def parse(reply: object, size: int) -> dict[int, str]:
    if not isinstance(reply, dict):
        message = "응답이 JSON 객체가 아니다"
        raise ReplyError(message)
    items = cast("dict[str, object]", reply).get("items")
    if not isinstance(items, list):
        message = "응답에 items 배열이 없다"
        raise ReplyError(message)
    found: dict[int, str] = {}
    for item in cast("list[object]", items):
        if not isinstance(item, dict):
            continue
        fields = cast("dict[str, object]", item)
        number = fields.get("id")
        text = fields.get("ko")
        if isinstance(number, int) and isinstance(text, str) and 0 <= number < size:
            found.setdefault(number, text)
    return found
