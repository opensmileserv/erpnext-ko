from dataclasses import dataclass
from typing import TYPE_CHECKING

from kotr.catalog import Entry
from kotr.markers import hangul_problems, marker_problems, shape_problems

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
        if entry.context is None:
            found += self.glossary.label_problems(entry.msgid, target, entry.apps, entry.skips)
        return found

    def review(self, entries: Iterable[Entry]) -> list[Finding]:
        findings: list[Finding] = []
        for entry in entries:
            problems = self.problems(entry)
            if problems:
                findings.append(Finding(entry, tuple(problems)))
        return findings
