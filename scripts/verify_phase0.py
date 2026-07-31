from __future__ import annotations

import compileall
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path | None = None) -> None:
    print(f"+ {' '.join(command)}")
    subprocess.run(command, cwd=cwd or ROOT, check=True, env=os.environ.copy())


def assert_no_committed_secrets() -> None:
    forbidden_files = [path for path in ROOT.rglob(".env") if path.is_file()]
    if forbidden_files:
        raise SystemExit(f"Committed .env files detected: {forbidden_files}")
    for example in ROOT.rglob("*.example"):
        text = example.read_text(encoding="utf-8")
        if "BEGIN PRIVATE KEY" in text:
            raise SystemExit(f"Private key material detected in {example}")


def assert_required_files() -> None:
    required = [
        ROOT / "backend" / "pyproject.toml",
        ROOT / "frontend" / "package.json",
        ROOT / "backend" / "alembic.ini",
        ROOT / "shared" / "openapi" / "options-scalper-v1.yaml",
        ROOT / ".env.example",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Required Phase 0 files missing: {missing}")


def main() -> None:
    assert_required_files()
    assert_no_committed_secrets()
    if not compileall.compile_dir(ROOT / "backend" / "src", quiet=1):
        raise SystemExit("Backend compilation failed")
    run([sys.executable, "-m", "pytest"], cwd=ROOT / "backend")
    print("Phase 0 local static checks passed.")
    print("External gate items still require PostgreSQL, frontend dependencies, and Public credentials.")


if __name__ == "__main__":
    main()
