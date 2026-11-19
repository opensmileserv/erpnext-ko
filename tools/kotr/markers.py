import re
from collections import Counter

URL_CHARS = r"A-Za-z0-9\-._~:/?#@!$&*+,;=%"
URL_END = r"A-Za-z0-9\-_~/#@$&+=%"
NAME = r"[A-Za-z0-9_]"
VALUE_CHARS = r"A-Za-z0-9_.{}%@:/+*-"
VALUE_END = r"A-Za-z0-9_{}%@/+*-"
MARKER = re.compile(
    r"\{\{.*?\}\}"
    r"|\{%.*?%\}"
    r"|\{[A-Za-z0-9_]*(?:[!:][^{}]*)?\}"
    r"|%\([A-Za-z_][A-Za-z0-9_]*\)[sdfr]"
    r"|%[sdfr]"
    r"|</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>"
    r"|&lt;/?[A-Za-z][A-Za-z0-9-]*(?:\s(?:(?!&gt;).)*)?/?&gt;"
    r"|&(?:[A-Za-z]+|#[0-9]+);"
    rf"|https?://[{URL_CHARS}]*[{URL_END}]"
    r"|`[^`\n]+`"
    r"|\$\{[^{}]*\}"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}"
    r"|(?<![A-Za-z0-9._%+-])@[A-Za-z][A-Za-z0-9_-]*"
    r"|(?<![A-Za-z0-9_./-])(?:application|multipart|text)/[a-z0-9][a-z0-9.+-]*[a-z0-9]"
    r"|(?<![A-Za-z0-9_.])[A-Za-z_][A-Za-z0-9_.]*\(\)"
    rf"|(?<![A-Za-z0-9_.])[A-Za-z_]{NAME}*=[{VALUE_CHARS}]*[{VALUE_END}]"
    rf"|(?<![A-Za-z0-9_.])[A-Za-z_]{NAME}+(?:\.[A-Za-z_]{NAME}*)+"
    rf"|(?<![A-Za-z0-9_.])(?={NAME}*[A-Za-z]){NAME}*_{NAME}*"
    r"|(?<![A-Za-z0-9_.])\.[a-z][a-z0-9]{1,4}(?![A-Za-z0-9_-])",
    re.DOTALL,
)
CODE = re.compile(r"<code\b[^>]*>.*?</code>", re.DOTALL)
LABEL = re.compile(rf"(?={NAME}*[A-Za-z]){NAME}*_{NAME}*")
MASK = "\x00"
HANGUL = re.compile(r"[가-힣]")
FOREIGN_SCRIPT = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")
WORD = re.compile(r"[A-Za-z][A-Za-z']+")
MIN_PROSE_WORD = 3


def markers(text: str) -> Counter[str]:
    return Counter(match.group(0) for match in MARKER.finditer(text))


def marker_problems(source: str, target: str) -> list[str]:
    if LABEL.fullmatch(source.strip()):
        return []
    expected = markers(source)
    actual = markers(target)
    missing = expected - actual
    extra = actual - expected
    problems = [f"빠진 표시 {marker!r}" for marker in sorted(missing.elements())]
    problems += [f"원문에 없는 표시 {marker!r}" for marker in sorted(extra.elements())]
    return problems


def leading(text: str) -> str:
    return text[: len(text) - len(text.lstrip())]


def trailing(text: str) -> str:
    return text[len(text.rstrip()) :]


def blank(match: re.Match[str]) -> str:
    return MASK * len(match.group(0))


def prose(text: str) -> str:
    return MARKER.sub(blank, CODE.sub(blank, text))


def prose_words(text: str) -> list[str]:
    return [
        word
        for word in WORD.findall(prose(text))
        if len(word) >= MIN_PROSE_WORD and any(char.islower() for char in word)
    ]


def shape_problems(source: str, target: str) -> list[str]:
    problems: list[str] = []
    if source.count("\n") != target.count("\n"):
        problems.append("줄바꿈 수가 원문과 다르다")
    if leading(source) != leading(target):
        problems.append("앞 공백이 원문과 다르다")
    if trailing(source) != trailing(target):
        problems.append("뒤 공백이 원문과 다르다")
    if FOREIGN_SCRIPT.search(target):
        problems.append("한자나 가나가 섞였다")
    return problems


def hangul_problems(source_prose: str, target: str) -> list[str]:
    if prose_words(source_prose) and not HANGUL.search(target):
        return ["한글이 없다 (번역되지 않았다)"]
    return []
