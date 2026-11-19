import io

from babel.messages.mofile import read_mo
from hypothesis import given
from hypothesis import strategies as st

from kotr.catalog import MACHINE, Entry, compile_mo, merge, parse, render, with_translation

TEXT = st.text(
    alphabet=st.characters(codec="utf-8", exclude_categories=("Cs", "Cc")), min_size=1, max_size=40
)


def entry(msgid: str, path: str = "erpnext/a.py", context: str | None = None) -> Entry:
    return Entry(msgid=msgid, context=context, locations=((path, 1),))


def test_merge_keeps_translations_and_flags() -> None:
    old = with_translation(entry("Item"), "품목", machine=True)
    merged, retired = merge([[entry("Item"), entry("Rate")]], [old])
    by_id = {item.msgid: item for item in merged}
    assert by_id["Item"].msgstr == "품목"
    assert MACHINE in by_id["Item"].flags
    assert by_id["Rate"].msgstr == ""
    assert retired == []


def test_merge_unions_locations_across_apps() -> None:
    merged, _ = merge([[entry("Save", "frappe/x.js")], [entry("Save", "erpnext/y.js")]], [])
    assert merged[0].apps == frozenset({"frappe", "erpnext"})


def test_vanished_translations_are_retired_and_revived() -> None:
    old = with_translation(entry("Old Label"), "옛 라벨", machine=False)
    merged, retired = merge([[entry("Item")]], [old])
    assert [item.msgid for item in retired] == ["Old Label"]
    revived, _ = merge([[entry("Old Label")]], merged, retired)
    assert revived[0].msgstr == "옛 라벨"


def test_contexts_are_separate_messages() -> None:
    merged, _ = merge([[entry("May", context="Month"), entry("May")]], [])
    assert len(merged) == 2


@given(st.lists(st.tuples(TEXT, TEXT, st.booleans()), max_size=12, unique_by=lambda row: row[0]))
def test_render_and_parse_round_trip(rows: list[tuple[str, str, bool]]) -> None:
    entries = [
        with_translation(entry(msgid), msgstr, machine=machine) for msgid, msgstr, machine in rows
    ]
    parsed, obsolete = parse(render(entries))
    assert obsolete == []
    assert [(item.msgid, item.msgstr, item.machine) for item in parsed] == [
        (item.msgid, item.msgstr, item.machine) for item in entries
    ]


def test_skip_comments_are_read() -> None:
    marked = Entry(msgid="Credit", comments=("glossary-skip: Credit",))
    assert marked.skips == frozenset({"credit"})


def test_compiled_mo_holds_only_translations_with_contexts() -> None:
    entries = [
        with_translation(entry("Item"), "품목", machine=True),
        entry("Rate"),
        with_translation(entry("May", context="Month"), "5월", machine=False),
    ]
    catalog = read_mo(io.BytesIO(compile_mo(entries)))
    found: dict[tuple[object, object], object] = {
        (message.id, message.context): message.string for message in catalog if message.id
    }
    expected: dict[tuple[object, object], object] = {
        ("Item", None): "품목",
        ("May", b"Month"): "5월",
    }
    assert found == expected
