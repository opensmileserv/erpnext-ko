from dataclasses import replace

from kotr.catalog import Entry
from kotr.glossary import Glossary, parse_terms
from kotr.review import Reviewer

HEADER = "en\tko\tavoid\tapps\tmatch\tnote"
REVIEWER = Reviewer(Glossary(parse_terms(f"{HEADER}\nSubmit\t확정|제출\t\t\tword\t")))
PLAIN = Entry("Submit", locations=(("frappe/public/js/form.js", 1),))


def test_a_label_without_context_takes_the_preferred_word() -> None:
    assert REVIEWER.problems(PLAIN, "확정") == []
    assert REVIEWER.problems(PLAIN, "제출") != []


def test_a_context_may_pick_another_variant() -> None:
    assert (
        REVIEWER.problems(replace(PLAIN, context="Submit password for Email Account"), "제출") == []
    )


LINKED = Entry(
    "Compare results. See [Quality Management](https://docs.frappe.io/q).",
    locations=(("erpnext/quality/x.json", 1),),
)


def test_link_labels_must_be_translated() -> None:
    assert (
        REVIEWER.problems(LINKED, "결과를 비교하세요. [품질 관리](https://docs.frappe.io/q) 참고.")
        == []
    )
    assert REVIEWER.problems(
        LINKED, "결과를 비교하세요. [Quality Management](https://docs.frappe.io/q) 참고."
    ) == ["링크 글자 'Quality Management' 가 번역되지 않았다"]


def test_kept_names_may_stay_in_link_labels() -> None:
    reviewer = Reviewer(Glossary(parse_terms(f"{HEADER}\nGitHub\tGitHub\t\t\tword\t")))
    entry = Entry(
        "Report it on [GitHub](https://github.com/frappe).", locations=(("frappe/x.py", 1),)
    )
    assert reviewer.problems(entry, "[GitHub](https://github.com/frappe)에 알려 주세요.") == []
