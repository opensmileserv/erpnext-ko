import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kotr.markers import HANGUL, MASK, prose

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

COLUMNS = ("en", "ko", "avoid", "apps", "match", "note")
EXACT = "exact"
WORD_MATCH = "word"
CASE_MATCH = "case"
MATCHES = (EXACT, WORD_MATCH, CASE_MATCH)


class GlossaryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Term:
    en: str
    ko: tuple[str, ...]
    avoid: tuple[str, ...]
    apps: frozenset[str]
    exact: bool
    case: bool
    note: str

    @property
    def preferred(self) -> str:
        return self.ko[0]

    @property
    def keep(self) -> bool:
        return self.preferred == self.en

    def applies_to(self, apps: frozenset[str]) -> bool:
        return not self.apps or bool(self.apps & apps)


@dataclass(frozen=True, slots=True)
class Hit:
    term: Term
    start: int
    end: int


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def phrase_pattern(en: str, *, case: bool = False) -> re.Pattern[str]:
    words = re.split(r"[\s-]+", en.strip())
    *head, last = words
    if last.isupper():
        tail = re.escape(last) + "s?"
    elif re.search(r"[^aeiouAEIOU]y$", last):
        tail = re.escape(last[:-1]) + "(?:y|ies)"
    elif last.isalpha():
        tail = re.escape(last) + "(?:s|es)?"
    else:
        tail = re.escape(last)
    body = r"[\s-]+".join([*map(re.escape, head), tail])
    flags = re.NOFLAG if case or en.isupper() else re.IGNORECASE
    return re.compile(rf"(?<![A-Za-z0-9_]){body}(?![A-Za-z0-9_])", flags)


def split_values(cell: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in cell.split("|") if value.strip())


def parse_terms(text: str) -> list[Term]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines or tuple(lines[0].split("\t")) != COLUMNS:
        message = f"용어집 첫 줄은 {'\\t'.join(COLUMNS)} 이어야 한다"
        raise GlossaryError(message)
    terms: list[Term] = []
    seen: set[tuple[str, frozenset[str]]] = set()
    for number, line in enumerate(lines[1:], start=2):
        cells = line.split("\t")
        if len(cells) != len(COLUMNS):
            message = f"용어집 {number}행: 칸이 {len(cells)}개다 ({len(COLUMNS)}개여야 한다)"
            raise GlossaryError(message)
        en, ko, avoid, apps, match, note = (cell.strip() for cell in cells)
        if match not in MATCHES:
            message = f"용어집 {number}행: match 는 {', '.join(MATCHES)} 중 하나다"
            raise GlossaryError(message)
        term = Term(
            en=en,
            ko=split_values(ko),
            avoid=split_values(avoid),
            apps=frozenset(app.strip() for app in apps.split(",") if app.strip()),
            exact=match == EXACT,
            case=match == CASE_MATCH,
            note=note,
        )
        if not term.en or not term.ko:
            message = f"용어집 {number}행: en 과 ko 는 비울 수 없다"
            raise GlossaryError(message)
        clash = [word for word in term.avoid if squash(word) in squash(term.preferred)]
        if clash:
            message = (
                f"용어집 {number}행: 권장 번역 {term.preferred!r} 가 피할 말 {clash} 를 품는다"
            )
            raise GlossaryError(message)
        key = (term.en.lower(), term.apps)
        if key in seen:
            message = f"용어집 {number}행: {term.en!r} 가 같은 범위에 두 번 있다"
            raise GlossaryError(message)
        seen.add(key)
        terms.append(term)
    return terms


class Glossary:
    def __init__(self, terms: Sequence[Term]) -> None:
        self.terms = tuple(terms)
        self._words = [
            (term, phrase_pattern(term.en, case=term.case), term.en.split()[0].lower())
            for term in sorted(self.terms, key=lambda term: -len(term.en))
            if not term.exact
        ]
        self._exact: dict[str, list[Term]] = {}
        for term in self.terms:
            if term.exact:
                self._exact.setdefault(term.en.lower(), []).append(term)

    def unwritten(self, msgid: str, apps: frozenset[str]) -> str:
        text = prose(msgid)
        for hit in self.hits(msgid, apps):
            if not HANGUL.search(hit.term.preferred):
                text = text[: hit.start] + MASK * (hit.end - hit.start) + text[hit.end :]
        return text

    def exact(self, msgid: str, apps: frozenset[str]) -> Term | None:
        for term in self._exact.get(msgid.strip().lower(), []):
            if term.applies_to(apps):
                return term
        for term, pattern, _ in self._words:
            if term.applies_to(apps) and pattern.fullmatch(msgid.strip()):
                return term
        return None

    def hits(self, msgid: str, apps: frozenset[str]) -> list[Hit]:
        exact = self.exact(msgid, apps)
        if exact is not None and exact.exact:
            return [Hit(exact, 0, len(msgid))]
        text = prose(msgid)
        lowered = text.lower()
        found = [
            Hit(term, match.start(), match.end())
            for term, pattern, first in self._words
            if first in lowered and term.applies_to(apps)
            for match in pattern.finditer(text)
        ]
        found.sort(key=lambda hit: (hit.start, hit.start - hit.end))
        chosen: list[Hit] = []
        for hit in found:
            if not chosen or hit.start >= chosen[-1].end:
                chosen.append(hit)
        return chosen

    def relevant(self, msgids: Iterable[tuple[str, frozenset[str]]]) -> list[Term]:
        terms: dict[str, Term] = {}
        for msgid, apps in msgids:
            for hit in self.hits(msgid, apps):
                terms.setdefault(hit.term.en.lower(), hit.term)
        return sorted(terms.values(), key=lambda term: term.en.lower())

    def label_problems(
        self, msgid: str, msgstr: str, apps: frozenset[str], skips: frozenset[str]
    ) -> list[str]:
        term = self.exact(msgid, apps)
        if term is None or term.en.lower() in skips:
            return []
        accepted = {squash(term.preferred), squash(msgid) if term.keep else squash(term.preferred)}
        if squash(msgstr) in accepted:
            return []
        return [f"용어집: 메시지 전체가 {term.en!r} 이면 {term.preferred!r} 로만 옮긴다"]

    def problems(
        self, msgid: str, msgstr: str, apps: frozenset[str], skips: frozenset[str]
    ) -> list[str]:
        target = squash(prose(msgstr))
        problems: list[str] = []
        for hit in self.hits(msgid, apps):
            term = hit.term
            if term.en.lower() in skips:
                continue
            written = (*term.ko, msgid[hit.start : hit.end]) if term.keep else term.ko
            if not any(squash(variant) in target for variant in written):
                problems.append(f"용어집: {term.en!r} 는 {term.preferred!r} 로 옮긴다")
            problems.extend(
                f"용어집: {term.en!r} 를 {word!r} 로 옮기지 않는다"
                for word in term.avoid
                if squash(word) in target
            )
        return problems
