import json
import re

import pytest

from kotr.catalog import Entry, with_translation
from kotr.glossary import Glossary, parse_terms
from kotr.translate import ReplyError, batches, build, parse, pick

GLOSSARY = Glossary(
    parse_terms(
        "en\tko\tavoid\tapps\tmatch\tnote\nStock\t재고\t주식\terpnext\tword\t주식과 다르다\n"
    )
)


def entry(msgid: str, path: str = "erpnext/stock/x.json", uses: int = 1) -> Entry:
    return Entry(msgid=msgid, locations=tuple((path, line) for line in range(uses)))


def test_pick_skips_done_and_filters_by_path_and_orders_by_use() -> None:
    done = with_translation(entry("Done"), "완료", machine=False)
    rare = entry("Rare label")
    common = entry("Common label", uses=5)
    core = entry("Core", path="frappe/core/x.py")
    chosen = pick([done, rare, common, core], re.compile(r"^erpnext/"), None)
    assert [item.msgid for item in chosen] == ["Common label", "Rare label"]


def test_batches_respect_both_limits() -> None:
    entries = [entry(f"Label {number}") for number in range(10)]
    groups = batches(entries, max_chars=10_000, max_items=4)
    assert [len(group) for group in groups] == [4, 4, 2]
    assert sum(len(group) for group in batches(entries, max_chars=1, max_items=40)) == 10


def test_build_carries_glossary_and_feedback() -> None:
    request = build([entry("Stock Level")], GLOSSARY, {0: ["용어집: 'Stock' 는 '재고' 로 옮긴다"]})
    assert "Stock → 재고 (피할 말: 주식) — 주식과 다르다" in request.user
    payload = json.loads(request.user.split("문구 (JSON):\n", 1)[1])
    assert payload == [
        {
            "id": 0,
            "en": "Stock Level",
            "where": "erpnext/stock/x.json",
            "fix": ["용어집: 'Stock' 는 '재고' 로 옮긴다"],
        }
    ]


def test_parse_accepts_known_ids_only() -> None:
    reply = {"items": [{"id": 0, "ko": "재고"}, {"id": 7, "ko": "범위 밖"}, {"id": "1", "ko": "x"}]}
    assert parse(reply, 2) == {0: "재고"}


def test_parse_rejects_wrong_shapes() -> None:
    with pytest.raises(ReplyError):
        parse([], 1)
    with pytest.raises(ReplyError):
        parse({"translations": []}, 1)
