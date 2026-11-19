import ast
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "erpnext_ko"
PUBLIC_JS = APP / "public" / "js"


def hook(name: str) -> object:
    tree = ast.parse((APP / "hooks.py").read_text(encoding="utf-8"))
    values = {
        target.id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    return ast.literal_eval(values[name])


def test_desk_bundle_and_its_imports_exist() -> None:
    bundle = hook("app_include_js")
    assert isinstance(bundle, str)
    source = (PUBLIC_JS / bundle).read_text(encoding="utf-8")
    imports = re.findall(r'^import "(\./[^"]+)";$', source, re.MULTILINE)
    assert imports
    assert all((PUBLIC_JS / path).is_file() for path in imports)
