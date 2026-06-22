from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5


def new_id() -> UUID:
    return uuid4()


def stable_id(*parts: object) -> UUID:
    return uuid5(NAMESPACE_URL, "finnews:" + ":".join(str(part) for part in parts))


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
