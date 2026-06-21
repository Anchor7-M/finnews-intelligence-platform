from __future__ import annotations


class FinnewsError(Exception):
    """Base application error."""


class ValidationError(FinnewsError):
    """Raised when source metadata cannot be accepted."""


class NotFoundError(FinnewsError):
    """Raised when a requested object is absent."""
