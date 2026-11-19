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
