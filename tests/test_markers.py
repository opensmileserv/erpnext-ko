from typing import TYPE_CHECKING

from hypothesis import given
from hypothesis import strategies as st

from kotr.markers import (
    hangul_problems,
    link_labels,
    marker_problems,
    markers,
    prose,
    shape_problems,
)

if TYPE_CHECKING:
    from random import Random

PLACEHOLDERS = st.sampled_from(
    ["{0}", "{1}", "{}", "{name}", "%s", "%(doctype)s", "<b>", "</b>", "<br>", "&nbsp;"]
)
WORDS = st.sampled_from(["Account", "is", "not", "valid", "for", "row", "the", "회계", "전표"])
NONE: frozenset[str] = frozenset()


@st.composite
def templated(draw: st.DrawFn) -> tuple[str, list[str]]:
    pieces: list[str] = []
    used: list[str] = []
    for _ in range(draw(st.integers(min_value=1, max_value=8))):
        if draw(st.booleans()):
            marker = draw(PLACEHOLDERS)
            used.append(marker)
            pieces.append(marker)
        else:
            pieces.append(draw(WORDS))
    return " ".join(pieces), used


@given(templated())
def test_markers_find_exactly_the_inserted_placeholders(case: tuple[str, list[str]]) -> None:
    text, used = case
    assert sorted(markers(text).elements()) == sorted(used)


@given(templated())
def test_identical_text_has_no_marker_problems(case: tuple[str, list[str]]) -> None:
    text, _ = case
    assert marker_problems(text, text) == []


@given(templated(), st.randoms())
def test_reordering_markers_is_allowed(case: tuple[str, list[str]], random: Random) -> None:
    text, _ = case
    pieces = text.split(" ")
    random.shuffle(pieces)
    assert marker_problems(text, " ".join(pieces)) == []


@given(templated())
def test_dropping_a_marker_is_reported(case: tuple[str, list[str]]) -> None:
    text, used = case
    if not used:
        return
    dropped = text.replace(used[0], "", 1)
    assert any(used[0] in problem for problem in marker_problems(text, dropped))


def test_jinja_and_html_attributes_are_kept_whole() -> None:
    source = 'Open <a href="/app/item">{{ doc.name }}</a>'
    assert marker_problems(source, '<a href="/app/item">{{ doc.name }}</a> 열기') == []
    assert marker_problems(source, '<a href="/app/품목">{{ doc.name }}</a> 열기') != []


def test_hangul_is_required_only_for_prose() -> None:
    assert hangul_problems("Save", "Save") == ["한글이 없다 (번역되지 않았다)"]
    assert hangul_problems("PDF", "PDF") == []
    assert hangul_problems("jane@example.com", "jane@example.com") == []
    assert hangul_problems(".csv, .xlsx", ".csv, .xlsx") == []
    assert hangul_problems('{0} ${skip_list ? "" : type}', '{0} ${skip_list ? "" : type}') == []


def test_shape_keeps_edges_and_rejects_hanja() -> None:
    assert "앞 공백이 원문과 다르다" in shape_problems(" Search", "검색")
    assert "뒤 공백이 원문과 다르다" in shape_problems("Total ", "합계")
    assert "한자나 가나가 섞였다" in shape_problems("Account", "計定 계정")
    assert shape_problems("Line 1\nLine 2", "1행\n2행") == []
    assert "줄바꿈 수가 원문과 다르다" in shape_problems("a\nb", "가 나")


def test_url_stops_before_korean_and_sentence_end() -> None:
    assert (
        marker_problems("See https://frappe.io/docs.", "https://frappe.io/docs를 참고하세요.") == []
    )
    assert marker_problems("URL must start with https://", "URL은 https://로 시작해야 합니다") == []


def test_code_names_in_sentences_are_kept() -> None:
    source = "Use doc.status or is_group, e.g. delete() with uid={0},dc=com for .csv files"
    assert sorted(markers(source)) == [
        ".csv",
        "dc=com",
        "delete()",
        "doc.status",
        "is_group",
        "uid={0}",
    ]
    assert (
        marker_problems("Ask @jane at jane@example.com", "jane@example.com 으로 @jane 에게 문의")
        == []
    )
    assert marker_problems("frappe.sendmail sends it", "Frappe.sendmail 이 보낸다") != []
    assert marker_problems("&lt;head&gt; HTML", "<head> HTML") != []
    assert markers("Use application/x-www-form-urlencoded or text/plain") == {
        "application/x-www-form-urlencoded": 1,
        "text/plain": 1,
    }


def test_a_bare_identifier_is_a_label() -> None:
    assert marker_problems("on_submit", "확정 시") == []
    assert marker_problems("on_submit", "on_submit") == []
    assert marker_problems("Robots.txt", "로보트.txt") != []


def test_prose_masks_code_without_joining_words() -> None:
    masked = prose("Open <code>Item</code> for {0} now")
    assert "Item" not in masked
    assert "{0}" not in masked
    assert len(masked) == len("Open <code>Item</code> for {0} now")
    assert "for" in masked.split()


def test_link_labels_cover_markdown_and_anchors() -> None:
    text = (
        'See [Quality Management](https://docs.frappe.io/q) or <a href="/app/task">Task list</a>.'
    )
    assert link_labels(text) == ["Quality Management", "Task list"]
    assert link_labels("[x] done, (see) [notes](not-a-link)") == []
