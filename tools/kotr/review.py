from dataclasses import dataclass
from typing import TYPE_CHECKING

from kotr.catalog import Entry
from kotr.markers import (
    hangul_problems,
    link_labels,
    marker_problems,
    prose_words,
    shape_problems,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from kotr.glossary import Glossary


@dataclass(frozen=True, slots=True)
class Finding:
    entry: Entry
    problems: tuple[str, ...]


class Reviewer:
    def __init__(self, glossary: Glossary) -> None:
        self.glossary = glossary

    def problems(self, entry: Entry, msgstr: str | None = None) -> list[str]:
        target = entry.msgstr if msgstr is None else msgstr
        if not target:
            return []
        found = marker_problems(entry.msgid, target)
        found += shape_problems(entry.msgid, target)
        found += hangul_problems(self.glossary.unwritten(entry.msgid, entry.apps), target)
        found += self.glossary.problems(entry.msgid, target, entry.apps, entry.skips)
        found += self.link_problems(entry, target)
        if entry.context is None:
            found += self.glossary.label_problems(entry.msgid, target, entry.apps, entry.skips)
        return found

    def link_problems(self, entry: Entry, target: str) -> list[str]:
        kept = set(link_labels(target))
        return [
            f"링크 글자 {label!r} 가 번역되지 않았다"
            for label in link_labels(entry.msgid)
            if label in kept and prose_words(self.glossary.unwritten(label, entry.apps))
        ]

    def review(self, entries: Iterable[Entry]) -> list[Finding]:
        findings: list[Finding] = []
        for entry in entries:
            problems = self.problems(entry)
            if problems:
                findings.append(Finding(entry, tuple(problems)))
        return findings
