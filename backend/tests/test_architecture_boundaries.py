import ast
from pathlib import Path


def test_strategy_does_not_import_adapters() -> None:
    strategy_root = Path(__file__).parents[1] / "src" / "scalper" / "strategy"
    violations: list[str] = []
    for path in strategy_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported = [node.module or ""]
            else:
                continue
            if any(
                name == "scalper.adapters" or name.startswith("scalper.adapters.")
                for name in imported
            ):
                violations.append(f"{path}:{node.lineno}")
    assert violations == []
