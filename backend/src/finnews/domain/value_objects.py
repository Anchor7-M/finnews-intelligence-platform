from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4


def new_id() -> UUID:
    return uuid4()


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class DateRange:
    start: date | None = None
    end: date | None = None

    def contains(self, value: date) -> bool:
        if self.start and value < self.start:
            return False
        return not (self.end and value > self.end)
