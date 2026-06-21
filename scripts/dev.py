from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path = ROOT, check: bool = True) -> int:
    resolved = command[:]
    executable = shutil.which(command[0])
    if executable:
        resolved[0] = executable
    print(f"+ {' '.join(command)}")
    completed = subprocess.run(resolved, cwd=cwd, check=False)
    if check and completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return completed.returncode


def doctor(_: argparse.Namespace) -> None:
    print(f"repo={ROOT}")
    run([sys.executable, "--version"], check=False)
    run(["node", "--version"], check=False)
    run(["npm", "--version"], check=False)
    run(["docker", "--version"], check=False)
    print(f"fixtures={(ROOT / 'data' / 'fixtures').exists()}")
    print(f"backend={(ROOT / 'backend' / 'pyproject.toml').exists()}")
    print(f"frontend={(ROOT / 'frontend' / 'package.json').exists()}")


def verify_lite(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    run([sys.executable, "-m", "pytest", "--cov=finnews", "--cov-report=term-missing", "--cov-fail-under=80"], backend)
    run([sys.executable, "-m", "ruff", "check", "."], backend)
    run([sys.executable, "-m", "ruff", "format", "--check", "."], backend)
    run([sys.executable, "-m", "mypy", "src", "tests"], backend)
    run(["npm", "run", "lint"], frontend)
    run(["npm", "run", "format:check"], frontend)
    run(["npm", "run", "typecheck"], frontend)
    run(["npm", "run", "test:unit", "--", "--run"], frontend)
    run(["npm", "run", "build"], frontend)
    run([sys.executable, "-m", "finnews.interfaces.cli.app", "demo", "--profile", "memory"], backend)
    validate_static_export()
    if shutil.which("git"):
        run(["git", "diff", "--check"], ROOT)


def validate_static_export() -> None:
    output = ROOT / "frontend" / "public" / "demo-data"
    required = ["overview.json", "articles.json", "companies.json", "digests.json", "signals.json"]
    missing = [name for name in required if not (output / name).is_file()]
    if missing:
        raise SystemExit(f"missing static demo files: {', '.join(missing)}")


def db_up(_: argparse.Namespace) -> None:
    run(["docker", "compose", "up", "-d", "postgres"])
    print("Stop with: python scripts/dev.py db-down")


def db_down(_: argparse.Namespace) -> None:
    run(["docker", "compose", "down"])


def verify_postgres(_: argparse.Namespace) -> None:
    try:
        db_up(argparse.Namespace())
        run([sys.executable, "-m", "alembic", "upgrade", "head"], ROOT / "backend")
        run([sys.executable, "-m", "pytest", "-m", "postgres"], ROOT / "backend")
    finally:
        db_down(argparse.Namespace())


def export_static(_: argparse.Namespace) -> None:
    run(
        [
            sys.executable,
            "-m",
            "finnews.interfaces.cli.app",
            "export-static",
            "--output",
            "../frontend/public/demo-data",
        ],
        ROOT / "backend",
    )
    validate_static_export()


def cleanup(args: argparse.Namespace) -> None:
    candidates = [
        ROOT / "backend" / ".pytest_cache",
        ROOT / "backend" / ".mypy_cache",
        ROOT / "backend" / ".ruff_cache",
        ROOT / "frontend" / "dist",
        ROOT / "frontend" / "coverage",
        ROOT / "data" / "generated",
    ]
    existing = [path for path in candidates if path.exists()]
    for path in existing:
        print(path)
    if args.dry_run or not args.confirm:
        print("Dry run only. Re-run with cleanup --confirm to remove repository-local generated files.")
        return
    for path in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor").set_defaults(func=doctor)
    sub.add_parser("verify-lite").set_defaults(func=verify_lite)
    sub.add_parser("db-up").set_defaults(func=db_up)
    sub.add_parser("db-down").set_defaults(func=db_down)
    sub.add_parser("verify-postgres").set_defaults(func=verify_postgres)
    sub.add_parser("export-static").set_defaults(func=export_static)
    cleanup_parser = sub.add_parser("cleanup")
    cleanup_parser.add_argument("--dry-run", action="store_true", default=False)
    cleanup_parser.add_argument("--confirm", action="store_true", default=False)
    cleanup_parser.set_defaults(func=cleanup)
    args = parser.parse_args()
    os.environ.setdefault("FINNEWS_PROFILE", "memory")
    args.func(args)


if __name__ == "__main__":
    main()
