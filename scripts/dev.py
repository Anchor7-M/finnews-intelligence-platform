from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
POSTGRES_PROJECT = "finnews_m1b_verify"
POSTGRES_SERVICE = "postgres"
POSTGRES_URL = "postgresql+psycopg://finnews:finnews@127.0.0.1:55432/finnews"


def run(
    command: list[str],
    cwd: Path = ROOT,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> int:
    resolved = command[:]
    executable = shutil.which(command[0])
    if executable:
        resolved[0] = executable
    print(f"+ {' '.join(command)}")
    completed = subprocess.run(
        resolved,
        cwd=cwd,
        check=False,
        env={**os.environ, **(env or {})},
    )
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
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--cov=finnews",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
        ],
        backend,
    )
    run([sys.executable, "-m", "ruff", "check", "."], backend)
    run([sys.executable, "-m", "ruff", "format", "--check", "."], backend)
    run([sys.executable, "-m", "mypy", "src", "tests"], backend)
    run(["npm", "run", "lint"], frontend)
    run(["npm", "run", "format:check"], frontend)
    run(["npm", "run", "typecheck"], frontend)
    run(["npm", "run", "test:unit", "--", "--run"], frontend)
    run(["npm", "run", "build"], frontend)
    run(
        [
            sys.executable,
            "-m",
            "finnews.interfaces.cli.app",
            "demo",
            "--profile",
            "memory",
        ],
        backend,
    )
    validate_static_export()
    if shutil.which("git"):
        run(["git", "diff", "--check"], ROOT)


def validate_static_export() -> None:
    output = ROOT / "frontend" / "public" / "demo-data"
    required = [
        "overview.json",
        "articles.json",
        "companies.json",
        "digests.json",
        "signals.json",
        "sources.json",
        "source-health.json",
        "source-fetch-attempts.json",
        "source-conditional-examples.json",
        "source-reviews.json",
        "source-review-examples.json",
    ]
    missing = [name for name in required if not (output / name).is_file()]
    if missing:
        raise SystemExit(f"missing static demo files: {', '.join(missing)}")


def db_up(_: argparse.Namespace) -> None:
    run(["docker", "compose", "-p", POSTGRES_PROJECT, "up", "-d", POSTGRES_SERVICE])
    wait_for_postgres_health()
    print("Stop with: python scripts/dev.py db-down")


def db_down(_: argparse.Namespace) -> None:
    run(
        [
            "docker",
            "compose",
            "-p",
            POSTGRES_PROJECT,
            "down",
            "--volumes",
            "--remove-orphans",
        ]
    )


def verify_postgres(_: argparse.Namespace) -> None:
    env = {
        "FINNEWS_PROFILE": "postgres",
        "FINNEWS_DATABASE_URL": POSTGRES_URL,
        "FINNEWS_RUN_POSTGRES_TESTS": "1",
    }
    success = False
    try:
        db_up(argparse.Namespace())
        run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            ROOT / "backend",
            env=env,
        )
        run(
            [sys.executable, "-m", "pytest", "-m", "postgres", "-s"],
            ROOT / "backend",
            env=env,
        )
        success = True
    finally:
        db_down(argparse.Namespace())
    if success:
        print(
            "verify-postgres passed: project=finnews_m1b_verify service=postgres "
            "image=postgres:16 port=127.0.0.1:55432"
        )


def verify_sources(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    env = {"FINNEWS_SOURCE_TEST_MODE": "mocked-offline"}
    run(
        [
            sys.executable,
            "-m",
            "finnews.interfaces.cli.app",
            "source",
            "validate-config",
        ],
        backend,
        env=env,
    )
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_source_registry.py",
            "tests/unit/test_http_safety.py",
            "tests/unit/test_source_adapters.py",
            "tests/unit/test_source_ingestion.py",
            "tests/contract/test_source_api_cli.py",
        ],
        backend,
        env=env,
    )
    run(["npm", "run", "test:unit", "--", "--run"], frontend, env=env)


def verify_source_reviews(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    env = {"FINNEWS_SOURCE_TEST_MODE": "mocked-offline"}
    run(
        [
            sys.executable,
            "-m",
            "finnews.interfaces.cli.app",
            "source",
            "review",
            "validate",
        ],
        backend,
        env=env,
    )
    run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_source_reviews.py",
            "tests/unit/test_source_overrides.py",
            "tests/unit/test_source_adapters.py",
            "tests/unit/test_source_smoke.py",
            "tests/contract/test_source_reviews_api.py",
        ],
        backend,
        env=env,
    )


def smoke_source(args: argparse.Namespace) -> None:
    command = [
        sys.executable,
        "-m",
        "finnews.interfaces.cli.app",
        "source",
        "smoke-test",
        "--source",
        args.source,
        "--max-items",
        str(args.max_items),
        "--no-persist",
    ]
    if args.conditional_check:
        command.append("--conditional-check")
    if args.confirm_live:
        command.append("--confirm-live")
    if args.report_path:
        command.extend(["--report-path", args.report_path])
    run(command, ROOT / "backend")


def wait_for_postgres_health(timeout_seconds: int = 90) -> None:
    container_id = _postgres_container_id()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Health.Status}}",
                container_id,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if status.stdout.strip() == "healthy":
            return
        time.sleep(2)
    run(["docker", "logs", container_id], check=False)
    raise SystemExit("PostgreSQL container did not become healthy before timeout")


def _postgres_container_id() -> str:
    completed = subprocess.run(
        ["docker", "compose", "-p", POSTGRES_PROJECT, "ps", "-q", POSTGRES_SERVICE],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    container_id = completed.stdout.strip()
    if not container_id:
        raise SystemExit("PostgreSQL container was not created")
    return container_id


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
        print(
            "Dry run only. Re-run with cleanup --confirm to remove repository-local generated files."
        )
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
    sub.add_parser("verify-sources").set_defaults(func=verify_sources)
    sub.add_parser("verify-source-reviews").set_defaults(func=verify_source_reviews)
    smoke_parser = sub.add_parser("smoke-source")
    smoke_parser.add_argument("--source", required=True)
    smoke_parser.add_argument("--max-items", type=int, default=5)
    smoke_parser.add_argument("--conditional-check", action="store_true", default=False)
    smoke_parser.add_argument("--confirm-live", action="store_true", default=False)
    smoke_parser.add_argument("--report-path")
    smoke_parser.set_defaults(func=smoke_source)
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
