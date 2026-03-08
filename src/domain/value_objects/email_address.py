from __future__ import annotations

import re

from src.domain.exceptions import ValidationError

EMAIL_REGEX = re.compile(r"^[\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}$", re.UNICODE)


class EmailAddress:
    """Immutable value object representing a validated email address."""

    def __init__(self, value: str) -> None:
        if not value or not EMAIL_REGEX.match(value):
            raise ValidationError(f"Invalid email address: '{value}'", field="email")
        object.__setattr__(self, "_value", value.lower().strip())

    @property
    def value(self) -> str:
        return self._value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EmailAddress):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"EmailAddress({self._value})"

    def __str__(self) -> str:
        return self._value

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("EmailAddress is immutable")
