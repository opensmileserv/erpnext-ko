import argparse
import os
import re
import sys
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from kotr.catalog import Entry, Key, compile_mo, merge, parse, render, with_translation
from kotr.desk import entries as desk_entries
from kotr.desk import load_documents
from kotr.glossary import Glossary, parse_terms
from kotr.llm import Provider, ProviderError, complete
from kotr.markers import leading, trailing
from kotr.review import Reviewer
from kotr.translate import ReplyError, build, pick, schema
from kotr.translate import batches as make_batches
from kotr.translate import parse as parse_reply

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[2]
PO = ROOT / "erpnext_ko" / "locale" / "ko.po"
TEMPLATES = (
    ROOT / "upstream" / "frappe.pot",
    ROOT / "upstream" / "erpnext.pot",
    ROOT / "upstream" / "desk.pot",
)
GLOSSARY = ROOT / "glossary" / "terms.tsv"
REJECTED = ROOT / "work" / "rejected.tsv"


def say(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def load_glossary() -> Glossary:
    return Glossary(parse_terms(GLOSSARY.read_text(encoding="utf-8")))


def load_po() -> tuple[list[Entry], list[Entry]]:
    if not PO.exists():
        return [], []
    return parse(PO.read_bytes())


def save_po(entries: Sequence[Entry], obsolete: Sequence[Entry]) -> None:
    PO.parent.mkdir(parents=True, exist_ok=True)
    temporary = PO.with_suffix(".po.tmp")
    temporary.write_bytes(render(entries, obsolete))
    temporary.replace(PO)


def command_extract_desk(arguments: argparse.Namespace) -> int:
    documents = load_documents(Path(arguments.source))
    found = desk_entries(documents)
    TEMPLATES[2].write_bytes(render(found))
    say(f"데스크 문서 {len(documents)}개에서 문구 {len(found)}개")
    return 0


def command_sync(_: argparse.Namespace) -> int:
    templates = [parse(path.read_bytes())[0] for path in TEMPLATES if path.exists()]
    current, obsolete = load_po()
    merged, retired = merge(templates, current, obsolete)
    save_po(merged, retired)
    known = {entry.key for entry in current}
    added = sum(1 for entry in merged if entry.key not in known)
    say(f"메시지 {len(merged)}개 (새로 {added}개), 원문에서 사라진 번역 {len(retired)}개 보관")
    return 0


def command_seed(_: argparse.Namespace) -> int:
    glossary = load_glossary()
    reviewer = Reviewer(glossary)
    current, obsolete = load_po()
    seeded = 0
    for number, entry in enumerate(current):
        if entry.translated:
            continue
        term = glossary.exact(entry.msgid, entry.apps)
        if term is None:
            continue
        text = leading(entry.msgid) + term.preferred + trailing(entry.msgid)
        if reviewer.problems(entry, text):
            continue
        current[number] = with_translation(entry, text, machine=False)
        seeded += 1
    save_po(current, obsolete)
    say(f"용어집으로 채운 메시지 {seeded}개")
    return 0


@dataclass(slots=True)
class Outcome:
    accepted: dict[Key, str] = field(default_factory=dict[Key, str])
    rejected: list[tuple[Entry, str, tuple[str, ...]]] = field(
        default_factory=list[tuple[Entry, str, tuple[str, ...]]]
    )
    prompt_tokens: int = 0
    completion_tokens: int = 0


def attempt(
    provider: Provider,
    glossary: Glossary,
    entries: Sequence[Entry],
    feedback: dict[int, list[str]] | None,
    outcome: Outcome,
) -> dict[int, str]:
    request = build(entries, glossary, feedback)
    reply = complete(provider, request.system, request.user, schema())
    outcome.prompt_tokens += reply.prompt_tokens
    outcome.completion_tokens += reply.completion_tokens
    return parse_reply(reply.content, len(entries))


def translate_group(
    provider: Provider, glossary: Glossary, reviewer: Reviewer, group: Sequence[Entry]
) -> Outcome:
    outcome = Outcome()
    found = attempt(provider, glossary, group, None, outcome)
    retry: list[Entry] = []
    feedback: dict[int, list[str]] = {}
    for number, entry in enumerate(group):
        text = found.get(number, "")
        problems = reviewer.problems(entry, text) if text else ["번역이 빠졌다"]
        if not problems:
            outcome.accepted[entry.key] = text
            continue
        feedback[len(retry)] = [*problems, f"앞선 번역: {text}"]
        retry.append(entry)
    if not retry:
        return outcome
    second = attempt(provider, glossary, retry, feedback, outcome)
    for number, entry in enumerate(retry):
        text = second.get(number, "")
        problems = reviewer.problems(entry, text) if text else ["번역이 빠졌다"]
        if problems:
            outcome.rejected.append((entry, text, tuple(problems)))
        else:
            outcome.accepted[entry.key] = text
    return outcome


def record_rejected(rejected: Sequence[tuple[Entry, str, tuple[str, ...]]]) -> None:
    if not rejected:
        return
    REJECTED.parent.mkdir(parents=True, exist_ok=True)
    with REJECTED.open("a", encoding="utf-8") as handle:
        for entry, text, problems in rejected:
            cells = [entry.msgid, text, " / ".join(problems)]
            handle.write("\t".join(cell.replace("\t", " ").replace("\n", "\\n") for cell in cells))
            handle.write("\n")


def command_translate(arguments: argparse.Namespace) -> int:
    provider = Provider.from_env(os.environ)
    glossary = load_glossary()
    reviewer = Reviewer(glossary)
    current, obsolete = load_po()
    where = re.compile(arguments.where) if arguments.where else None
    todo = pick(current, where, arguments.limit)
    groups = make_batches(todo, arguments.batch_chars, arguments.batch_items)
    index = {entry.key: number for number, entry in enumerate(current)}
    say(f"번역할 메시지 {len(todo)}개, 요청 {len(groups)}번, 동시 {arguments.jobs}개")
    started = time.monotonic()
    totals = Outcome()
    failed = 0
    with ThreadPoolExecutor(max_workers=arguments.jobs) as pool:
        futures: dict[Future[Outcome], int] = {
            pool.submit(translate_group, provider, glossary, reviewer, group): len(group)
            for group in groups
        }
        for done, future in enumerate(as_completed(futures), start=1):
            try:
                outcome = future.result()
            except (ProviderError, OSError) as error:
                failed += 1
                say(f"[{done}/{len(groups)}] 요청 실패: {error}")
                continue
            except (ReplyError, ValueError) as error:
                say(f"[{done}/{len(groups)}] 답을 읽지 못했다: {error}")
                continue
            for key, text in outcome.accepted.items():
                position = index[key]
                current[position] = with_translation(current[position], text, machine=True)
            totals.accepted.update(outcome.accepted)
            totals.rejected.extend(outcome.rejected)
            totals.prompt_tokens += outcome.prompt_tokens
            totals.completion_tokens += outcome.completion_tokens
            record_rejected(outcome.rejected)
            if done % arguments.save_every == 0 or done == len(groups):
                save_po(current, obsolete)
            elapsed = time.monotonic() - started
            say(
                f"[{done}/{len(groups)}] 받음 {len(totals.accepted)} · 거절 {len(totals.rejected)}"
                f" · 토큰 {totals.prompt_tokens}/{totals.completion_tokens} · {elapsed:.0f}초"
            )
    save_po(current, obsolete)
    if failed:
        say(f"모델 요청 {failed}번이 실패했다. 다시 실행하면 남은 메시지만 옮긴다")
        return 1
    return 0


def command_review(arguments: argparse.Namespace) -> int:
    reviewer = Reviewer(load_glossary())
    current, obsolete = load_po()
    findings = reviewer.review(current)
    if arguments.reset:
        cleared = {finding.entry.key for finding in findings if finding.entry.machine}
        current = [
            with_translation(entry, "", machine=False) if entry.key in cleared else entry
            for entry in current
        ]
        save_po(current, obsolete)
        findings = [finding for finding in findings if finding.entry.key not in cleared]
        say(f"문제가 있는 기계 번역 {len(cleared)}개를 비웠다 (translate 로 다시 옮긴다)")
    for finding in findings[: arguments.max]:
        entry = finding.entry
        say(f"- {entry.msgid!r} → {entry.msgstr!r}")
        for problem in finding.problems:
            say(f"    {problem}")
    translated = sum(1 for entry in current if entry.translated)
    say(f"번역 {translated}개 중 문제 {len(findings)}개")
    return 1 if findings else 0


def command_compile(arguments: argparse.Namespace) -> int:
    current, _ = load_po()
    output = Path(arguments.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(compile_mo(current))
    say(f"{output} 에 번역 {sum(1 for entry in current if entry.translated)}개를 컴파일했다")
    return 0


def command_stats(_: argparse.Namespace) -> int:
    current, obsolete = load_po()
    total = len(current)
    translated = [entry for entry in current if entry.translated]
    machine = sum(1 for entry in translated if entry.machine)
    say(f"전체 {total} · 번역 {len(translated)} ({100 * len(translated) / max(total, 1):.1f}%)")
    say(f"  기계 번역(mt) {machine} · 그 밖 {len(translated) - machine} · 보관 {len(obsolete)}")
    for app in ("frappe", "erpnext"):
        scoped = [entry for entry in current if app in entry.apps]
        done = sum(1 for entry in scoped if entry.translated)
        say(f"  {app}: {done}/{len(scoped)} ({100 * done / max(len(scoped), 1):.1f}%)")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="kotr", description="ERPNext 한국어 번역 도구")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="upstream/*.pot 을 ko.po 에 합친다").set_defaults(
        run=command_sync
    )
    extract = commands.add_parser(
        "extract-desk",
        help="upstream pot 에 빠진 데스크 문서(사이드바·아이콘·차트·숫자 카드) 문구를 "
        "upstream/desk.pot 로 뽑는다",
    )
    extract.add_argument("source", help="apps 디렉터리 (frappe/frappe/..., erpnext/erpnext/...)")
    extract.set_defaults(run=command_extract_desk)
    commands.add_parser("seed", help="용어집과 똑같은 메시지를 채운다").set_defaults(
        run=command_seed
    )
    translate = commands.add_parser("translate", help="모델로 빈 메시지를 옮긴다")
    translate.add_argument("--where", help="참조 경로 정규식 (예: erpnext/accounts/)")
    translate.add_argument("--limit", type=int)
    translate.add_argument("--jobs", type=int, default=2)
    translate.add_argument("--batch-chars", type=int, default=2400)
    translate.add_argument("--batch-items", type=int, default=40)
    translate.add_argument("--save-every", type=int, default=5)
    translate.set_defaults(run=command_translate)
    review = commands.add_parser("review", help="번역을 검사한다 (문제가 있으면 1)")
    review.add_argument("--max", type=int, default=50)
    review.add_argument(
        "--reset", action="store_true", help="문제가 있는 기계 번역(mt)을 비워 다시 옮기게 한다"
    )
    review.set_defaults(run=command_review)
    compile_parser = commands.add_parser("compile", help="ko.po 를 .mo 로 컴파일한다")
    compile_parser.add_argument("--out", default=str(ROOT / "work" / "erpnext_ko.mo"))
    compile_parser.set_defaults(run=command_compile)
    commands.add_parser("stats", help="번역 현황").set_defaults(run=command_stats)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    run = arguments.run
    return int(run(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
