from pathlib import Path

import pytest

from kotr.glossary import Glossary, GlossaryError, parse_terms
from kotr.markers import hangul_problems

HEADER = "en\tko\tavoid\tapps\tmatch\tnote"
ERP = frozenset({"erpnext"})
CORE = frozenset({"frappe"})


def glossary(*rows: str) -> Glossary:
    return Glossary(parse_terms("\n".join([HEADER, *rows])))


SAMPLE = glossary(
    "Journal Entry\t전표\t일지\terpnext\tword\t",
    "Stock\t재고\t주식\terpnext\tword\t",
    "Stock Entry\t재고 입출고\t\terpnext\tword\t",
    "Item\t품목\t아이템\terpnext\tword\t",
    "Rate\t단가\t\terpnext\texact\t",
    "Credit\t대변\t신용 거래\terpnext\tword\t",
    "Credit Card\t신용카드\t\t\tword\t",
    "Google\tGoogle\t구글\t\tword\t",
)


def test_longest_phrase_wins_and_plural_matches() -> None:
    hits = SAMPLE.hits("Stock Entries for Item", ERP)
    assert [hit.term.en for hit in hits] == ["Stock Entry", "Item"]


def test_scope_limits_terms_to_their_app() -> None:
    assert SAMPLE.hits("Item", CORE) == []
    assert SAMPLE.problems("Item", "항목", CORE, frozenset()) == []
    assert SAMPLE.problems("Item", "항목", ERP, frozenset()) != []


def test_required_and_avoided_words() -> None:
    assert SAMPLE.problems("Stock Entry", "재고 입출고", ERP, frozenset()) == []
    assert SAMPLE.problems("Stock", "주식", ERP, frozenset()) == [
        "용어집: 'Stock' 는 '재고' 로 옮긴다",
        "용어집: 'Stock' 를 '주식' 로 옮기지 않는다",
    ]


def test_spacing_does_not_matter() -> None:
    assert SAMPLE.problems("Journal Entry", "전 표", ERP, frozenset()) == []
    assert SAMPLE.problems("Stock Entry", "재고입출고", ERP, frozenset()) == []


def test_longer_term_shields_shorter_one() -> None:
    assert SAMPLE.problems("Pay by Credit Card", "신용카드로 결제", ERP, frozenset()) == []


def test_exact_terms_only_apply_to_whole_messages() -> None:
    assert SAMPLE.problems("Rate", "요율", ERP, frozenset()) != []
    assert SAMPLE.problems("Interest Rate", "이자율", ERP, frozenset()) == []
    term = SAMPLE.exact("Rate", ERP)
    assert term is not None
    assert term.preferred == "단가"


def test_skip_comment_silences_one_term() -> None:
    assert SAMPLE.problems("Credit", "신용 거래", ERP, frozenset({"credit"})) == []


def test_keep_terms_must_stay_in_english() -> None:
    assert SAMPLE.problems("Sign in with Google", "구글로 로그인", CORE, frozenset()) != []
    assert SAMPLE.problems("Sign in with Google", "Google 로 로그인", CORE, frozenset()) == []
    assert SAMPLE.problems("google", "google", CORE, frozenset()) == []


def test_hangul_free_terms_are_not_prose() -> None:
    names = glossary(
        "Office 365\tOffice 365\t\t\tword\t",
        "Point of Sale\tPOS\t\terpnext\tword\t",
        "Public\t공개\t\t\tword\t",
    )
    assert hangul_problems(names.unwritten("Office 365", CORE), "Office 365") == []
    assert hangul_problems(names.unwritten("Point of Sale", ERP), "POS") == []
    assert hangul_problems(names.unwritten("Open Point of Sale", ERP), "POS") != []
    assert hangul_problems(names.unwritten("Public", CORE), "Public") != []


def test_terms_inside_code_are_not_hits() -> None:
    source = "See https://docs.frappe.io/item, {item_code}, get_item(), <code>Item</code>"
    assert SAMPLE.hits(source, ERP) == []
    assert [hit.term.en for hit in SAMPLE.hits("Item {item_code}", ERP)] == ["Item"]


def test_masking_does_not_join_neighbours() -> None:
    terms = glossary("Against Account\t상대 계정\t계정에 대해\terpnext\tword\t")
    assert (
        terms.problems("for {1} against account {2}", "상대 계정 {2}에 대해", ERP, frozenset())
        == []
    )


def test_acronyms_and_case_terms_match_their_case() -> None:
    terms = glossary("HR\t인사\t\t\tword\t", "Lead\t리드\t\terpnext\tcase\t")
    assert terms.hits("6 hrs", CORE) == []
    assert [hit.term.en for hit in terms.hits("HR Settings", CORE)] == ["HR"]
    assert (
        terms.problems("This may lead to errors", "오류가 날 수 있습니다", ERP, frozenset()) == []
    )
    assert terms.problems("Lead {0} exists", "잠재 {0} 있음", ERP, frozenset()) != []


def test_whole_message_exact_term_shields_word_terms() -> None:
    terms = glossary("Account\t계정\t\terpnext\tword\t", "Accounts\t회계|계정\t\terpnext\texact\t")
    assert [hit.term.en for hit in terms.hits("Accounts", ERP)] == ["Accounts"]
    assert terms.problems("Accounts", "회계", ERP, frozenset()) == []
    assert [hit.term.en for hit in terms.hits("Accounts Settings", ERP)] == ["Account"]


def test_a_whole_message_term_takes_the_preferred_word() -> None:
    terms = glossary("Accounts\t회계|계정\t\terpnext\texact\t", "Facebook\tFacebook\t\t\tword\t")
    assert terms.label_problems("Accounts", "계정", ERP, frozenset()) != []
    assert terms.label_problems("Accounts", "회계", ERP, frozenset()) == []
    assert terms.label_problems("Accounts", "계정", ERP, frozenset({"accounts"})) == []
    assert terms.label_problems("facebook", "facebook", CORE, frozenset()) == []
    assert terms.label_problems("Open Accounts", "계정 열기", ERP, frozenset()) == []


def test_bad_rows_are_rejected() -> None:
    with pytest.raises(GlossaryError, match="칸이"):
        parse_terms(f"{HEADER}\nItem\t품목")
    with pytest.raises(GlossaryError, match="두 번"):
        parse_terms(f"{HEADER}\nItem\t품목\t\t\tword\t\nitem\t항목\t\t\tword\t")
    with pytest.raises(GlossaryError, match="피할 말"):
        parse_terms(f"{HEADER}\nStock\t주식 재고\t주식\t\tword\t")
    with pytest.raises(GlossaryError, match="match"):
        parse_terms(f"{HEADER}\nStock\t재고\t\t\tfuzzy\t")


def test_shipped_glossary_is_valid() -> None:
    path = Path(__file__).resolve().parents[1] / "glossary" / "terms.tsv"
    terms = parse_terms(path.read_text(encoding="utf-8"))
    assert len(terms) > 200
