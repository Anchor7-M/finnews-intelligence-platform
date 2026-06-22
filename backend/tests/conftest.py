from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("FINNEWS_RUN_POSTGRES_TESTS") == "1":
        return
    skip_postgres = pytest.mark.skip(reason="set FINNEWS_RUN_POSTGRES_TESTS=1")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip_postgres)
