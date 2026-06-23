from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POSTGRES_PROJECT = "finnews_m3b_verify"
POSTGRES_SERVICE = "postgres"
POSTGRES_URL = "postgresql+psycopg://finnews:finnews@127.0.0.1:55432/finnews"
TIMINGS: list[dict[str, Any]] = []
TIMINGS_PATH = ROOT / "reports" / "verification" / "revised-m3a-timings.json"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
PYTHON = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))
RUN_STARTED = time.monotonic()


def run(
    command: list[str],
    cwd: Path = ROOT,
    check: bool = True,
    env: dict[str, str] | None = None,
    timeout_seconds: int = 600,
    step_name: str | None = None,
) -> int:
    resolved = command[:]
    executable = shutil.which(command[0])
    if executable:
        resolved[0] = executable
    print(f"+ {' '.join(command)}")
    started = time.monotonic()
    status = "completed"
    try:
        completed = subprocess.run(
            resolved,
            cwd=cwd,
            check=False,
            env={**os.environ, **(env or {})},
            timeout=timeout_seconds,
        )
        return_code = completed.returncode
    except subprocess.TimeoutExpired:
        status = "timeout"
        return_code = 124
    duration = time.monotonic() - started
    ended = started + duration
    report_command = stable_command(command)
    _record_timing(
        {
            "step": step_name or " ".join(report_command[:4]),
            "command": report_command,
            "cwd": str(cwd.relative_to(ROOT)) if cwd.is_relative_to(ROOT) else str(cwd),
            "started_offset_seconds": round(started - RUN_STARTED, 3),
            "ended_offset_seconds": round(ended - RUN_STARTED, 3),
            "duration_seconds": round(duration, 3),
            "exit_code": return_code,
            "timeout_seconds": timeout_seconds,
            "outcome": status if return_code == 0 else f"{status}_failed",
        }
    )
    if status == "timeout":
        print(f"timed out after {timeout_seconds}s: {' '.join(command)}")
    if check and return_code != 0:
        raise SystemExit(return_code)
    return return_code


def stable_command(command: list[str]) -> list[str]:
    stable: list[str] = []
    for item in command:
        if item == PYTHON:
            stable.append(".venv/Scripts/python.exe" if VENV_PYTHON.exists() else "python")
            continue
        try:
            path = Path(item)
        except ValueError:
            stable.append(item)
            continue
        if path.is_absolute():
            try:
                stable.append(path.relative_to(ROOT).as_posix())
            except ValueError:
                stable.append("<external-path>")
        else:
            stable.append(item)
    return stable


def _record_timing(row: dict[str, Any]) -> None:
    if not TIMINGS and TIMINGS_PATH.exists():
        import json

        try:
            existing = json.loads(TIMINGS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        TIMINGS.extend(existing.get("steps", []))
    TIMINGS.append(row)
    TIMINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TIMINGS_PATH.write_text(
        json_dumps({"steps": TIMINGS}, indent=2),
        encoding="utf-8",
    )


def json_dumps(payload: object, indent: int | None = None) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True) + "\n"


@contextmanager
def tempfile_directory():
    path = Path(tempfile.mkdtemp(prefix="finnews-research-verify-"))
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@contextmanager
def temporary_signal_package():
    path = ROOT / ".finnews-market-signals" / "verify"
    if path.exists():
        shutil.rmtree(path)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def doctor(_: argparse.Namespace) -> None:
    print(f"repo={ROOT}")
    run([PYTHON, "--version"], check=False)
    run(["node", "--version"], check=False)
    run(["npm", "--version"], check=False)
    run(["docker", "--version"], check=False)
    print(f"fixtures={(ROOT / 'data' / 'fixtures').exists()}")
    print(f"backend={(ROOT / 'backend' / 'pyproject.toml').exists()}")
    print(f"frontend={(ROOT / 'frontend' / 'package.json').exists()}")


def verify_lite(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    run_backend_non_postgres_tests_with_coverage(backend)
    run([PYTHON, "-m", "ruff", "check", "."], backend, timeout_seconds=120)
    run([PYTHON, "-m", "ruff", "format", "--check", "."], backend, timeout_seconds=120)
    run([PYTHON, "-m", "mypy", "src", "tests"], backend, timeout_seconds=240)
    run(["npm", "run", "lint"], frontend, timeout_seconds=120)
    run(["npm", "run", "format:check"], frontend, timeout_seconds=120)
    run(["npm", "run", "typecheck"], frontend, timeout_seconds=180)
    run(["npm", "run", "test:unit", "--", "--run"], frontend, timeout_seconds=180)
    run(["npm", "run", "build"], frontend, timeout_seconds=240)
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "demo",
            "--profile",
            "memory",
        ],
        backend,
        timeout_seconds=180,
    )
    validate_static_export()
    if shutil.which("git"):
        run(["git", "diff", "--check"], ROOT, timeout_seconds=120)


def backend_non_postgres_test_files(backend: Path) -> list[str]:
    files = sorted((backend / "tests" / "unit").glob("test_*.py"))
    files += sorted((backend / "tests" / "contract").glob("test_*.py"))
    return [path.relative_to(backend).as_posix() for path in files]


def run_backend_non_postgres_tests_with_coverage(backend: Path) -> None:
    run([PYTHON, "-m", "coverage", "erase"], backend, timeout_seconds=60)
    for test_file in backend_non_postgres_test_files(backend):
        run(
            [
                PYTHON,
                "-m",
                "coverage",
                "run",
                "--parallel-mode",
                "-m",
                "pytest",
                test_file,
                "-q",
            ],
            backend,
            timeout_seconds=240,
            step_name=f"backend pytest coverage {test_file}",
        )
    run(
        [
            PYTHON,
            "-m",
            "coverage",
            "combine",
        ],
        backend,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "coverage",
            "report",
            "--fail-under=80",
            "--show-missing",
        ],
        backend,
        timeout_seconds=180,
    )


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
        "nlp-overview.json",
        "nlp-models.json",
        "nlp-evaluations.json",
        "nlp-error-analysis.json",
        "nlp-dataset-card.json",
        "research-overview.json",
        "research-calendars.json",
        "research-exports.json",
        "research-feature-catalog.json",
        "research-feature-sample.json",
        "research-lineage-sample.json",
        "research-quality-report.json",
        "research-leakage-audit.json",
        "cross-asset-overview.json",
        "assets.json",
        "asset-aliases.json",
        "asset-relationships.json",
        "cross-asset-events.json",
        "event-impacts.json",
        "market-signals.json",
        "mt5-readiness.json",
        "market-signal-contract-example.json",
        "official-data-overview.json",
        "official-datasets.json",
        "official-series.json",
        "official-observations.json",
        "official-observation-revisions.json",
        "official-regulatory-documents.json",
        "official-series-asset-associations.json",
        "official-release-events.json",
        "official-data-release-runs.json",
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
            [PYTHON, "-m", "alembic", "upgrade", "head"],
            ROOT / "backend",
            env=env,
            timeout_seconds=120,
        )
        for nodeid in collect_postgres_test_nodeids(ROOT / "backend", env):
            run(
                [PYTHON, "-m", "pytest", nodeid, "-s", "-q"],
                ROOT / "backend",
                env=env,
                timeout_seconds=300,
                step_name=f"postgres pytest {nodeid}",
            )
        success = True
    finally:
        db_down(argparse.Namespace())
    if success:
        print(
            "verify-postgres passed: project=finnews_m3b_verify service=postgres "
            "image=postgres:16 port=127.0.0.1:55432"
        )


def collect_postgres_test_nodeids(backend: Path, env: dict[str, str]) -> list[str]:
    command = [
        PYTHON,
        "-m",
        "pytest",
        "--collect-only",
        "-vv",
        "-m",
        "postgres",
    ]
    resolved = command[:]
    executable = shutil.which(command[0])
    if executable:
        resolved[0] = executable
    print(f"+ {' '.join(command)}")
    started = time.monotonic()
    completed = subprocess.run(
        resolved,
        cwd=backend,
        check=False,
        text=True,
        capture_output=True,
        env={**os.environ, **env},
        timeout=180,
    )
    duration = time.monotonic() - started
    ended = started + duration
    _record_timing(
        {
            "step": "postgres pytest collect",
            "command": stable_command(command),
            "cwd": str(backend.relative_to(ROOT)),
            "started_offset_seconds": round(started - RUN_STARTED, 3),
            "ended_offset_seconds": round(ended - RUN_STARTED, 3),
            "duration_seconds": round(duration, 3),
            "exit_code": completed.returncode,
            "timeout_seconds": 180,
            "outcome": "completed" if completed.returncode == 0 else "completed_failed",
        }
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        raise SystemExit(completed.returncode)
    nodeids: list[str] = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if "::test_" in stripped and not stripped.startswith("<"):
            nodeids.append(stripped)
        elif stripped.startswith("<Function test_") and stripped.endswith(">"):
            name = stripped.removeprefix("<Function ").removesuffix(">")
            nodeids.append(f"tests/integration/test_postgres_integration.py::{name}")
    if not nodeids:
        raise SystemExit("no PostgreSQL test nodeids collected")
    return nodeids


def verify_sources(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    env = {"FINNEWS_SOURCE_TEST_MODE": "mocked-offline"}
    run(
        [
            PYTHON,
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
            PYTHON,
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
            PYTHON,
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
            PYTHON,
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


def build_nlp_benchmark(_: argparse.Namespace) -> None:
    run(
        [PYTHON, "-m", "finnews.interfaces.cli.app", "nlp", "dataset", "build"],
        ROOT / "backend",
    )
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "nlp",
            "dataset",
            "validate",
        ],
        ROOT / "backend",
    )


def benchmark_nlp(_: argparse.Namespace) -> None:
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "nlp",
            "benchmark",
            "--task",
            "all",
        ],
        ROOT / "backend",
        env={
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        },
    )


def verify_ml(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    build_nlp_benchmark(argparse.Namespace())
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "tests/unit/test_nlp_baselines.py",
            "tests/unit/test_nlp_benchmark.py",
            "tests/unit/test_nlp_evaluation.py",
            "tests/unit/test_nlp_registry.py",
            "tests/unit/test_nlp_release_audit.py",
            "tests/contract/test_nlp_api.py",
        ],
        backend,
        env={"FINNEWS_SOURCE_TEST_MODE": "mocked-offline"},
    )
    benchmark_nlp(argparse.Namespace())
    run(
        [PYTHON, "-m", "finnews.interfaces.cli.app", "nlp", "release-audit"],
        backend,
    )
    run(
        [PYTHON, "-m", "finnews.interfaces.cli.app", "nlp", "export-static"],
        backend,
    )
    validate_static_export()


def verify_research_export(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    with tempfile_directory() as temp_root:
        left = temp_root / "left"
        right = temp_root / "right"
        run(
            [
                PYTHON,
                "-m",
                "finnews.interfaces.cli.app",
                "research",
                "calendar",
                "build-demo",
            ],
            backend,
        )
        for output in [left, right]:
            run(
                [
                    PYTHON,
                    "-m",
                    "finnews.interfaces.cli.app",
                    "research",
                    "export",
                    "build",
                    "--profile",
                    "memory",
                    "--output",
                    str(output),
                ],
                backend,
            )
            run(
                [
                    PYTHON,
                    "-m",
                    "finnews.interfaces.cli.app",
                    "research",
                    "export",
                    "validate",
                    "--path",
                    str(output),
                ],
                backend,
            )
        run(
            [
                PYTHON,
                "-m",
                "finnews.interfaces.cli.app",
                "research",
                "export",
                "compare",
                "--left",
                str(left),
                "--right",
                str(right),
            ],
            backend,
        )
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "tests/unit/test_research_export.py",
            "tests/contract/test_research_api_cli.py",
        ],
        backend,
    )


def verify_cross_asset(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    run(
        [PYTHON, "-m", "finnews.interfaces.cli.app", "asset", "validate"],
        backend,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "cross-asset",
            "build-demo",
        ],
        backend,
        timeout_seconds=120,
    )
    run(
        [PYTHON, "-m", "finnews.interfaces.cli.app", "cross-asset", "summary"],
        backend,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "cross-asset",
            "release-audit",
        ],
        backend,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "mt5",
            "readiness",
        ],
        backend,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "mt5",
            "validate-symbol-map",
            "--path",
            "../config/integrations/mt5-symbol-map.example.yaml",
        ],
        backend,
        timeout_seconds=120,
    )
    with temporary_signal_package() as output:
        run(
            [
                PYTHON,
                "-m",
                "finnews.interfaces.cli.app",
                "signal",
                "export",
                "--output",
                str(output),
            ],
            backend,
            timeout_seconds=120,
        )
        run(
            [
                PYTHON,
                "-m",
                "finnews.interfaces.cli.app",
                "signal",
                "validate",
                "--path",
                str(output),
            ],
            backend,
            timeout_seconds=120,
        )
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "tests/unit/test_cross_asset.py",
            "tests/contract/test_cross_asset_api_cli.py",
        ],
        backend,
        timeout_seconds=240,
    )


def verify_official_data(_: argparse.Namespace) -> None:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    env = {"FINNEWS_SOURCE_TEST_MODE": "mocked-offline"}
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "official-data",
            "validate-fixtures",
        ],
        backend,
        env=env,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "official-data",
            "export-static",
        ],
        backend,
        env=env,
        timeout_seconds=120,
    )
    run(
        [
            PYTHON,
            "-m",
            "pytest",
            "tests/unit/test_official_data.py",
            "tests/contract/test_official_data_api_cli.py",
        ],
        backend,
        env=env,
        timeout_seconds=240,
    )
    run(["npm", "run", "test:unit", "--", "--run"], frontend, env=env, timeout_seconds=180)
    validate_static_export()


def build_research_export(_: argparse.Namespace) -> None:
    output = ROOT / ".finnews-research-exports" / "latest"
    if output.exists():
        shutil.rmtree(output)
    run(
        [
            PYTHON,
            "-m",
            "finnews.interfaces.cli.app",
            "research",
            "export",
            "build",
            "--profile",
            "memory",
            "--output",
            str(output),
        ],
        ROOT / "backend",
    )


def smoke_source(args: argparse.Namespace) -> None:
    command = [
        PYTHON,
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
            PYTHON,
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
        ROOT / ".finnews-research-exports",
        ROOT / ".finnews-market-signals",
    ]
    existing = [path for path in candidates if path.exists()]
    for path in existing:
        print(path)
    if args.dry_run or not args.confirm:
        print(
            "Dry run only. Re-run with cleanup --confirm to remove "
            "repository-local generated files."
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
    sub.add_parser("verify-ml").set_defaults(func=verify_ml)
    sub.add_parser("verify-research-export").set_defaults(func=verify_research_export)
    sub.add_parser("verify-cross-asset").set_defaults(func=verify_cross_asset)
    sub.add_parser("verify-official-data").set_defaults(func=verify_official_data)
    sub.add_parser("build-research-export").set_defaults(func=build_research_export)
    sub.add_parser("build-nlp-benchmark").set_defaults(func=build_nlp_benchmark)
    sub.add_parser("benchmark-nlp").set_defaults(func=benchmark_nlp)
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
