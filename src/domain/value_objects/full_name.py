from __future__ import annotations

from src.domain.exceptions import ValidationError


class FullName:
    """Immutable value object representing a person's full name."""

    def __init__(self, first_name: str, last_name: str) -> None:
        if not first_name or not first_name.strip():
            raise ValidationError("First name cannot be empty", field="first_name")
        if not last_name or not last_name.strip():
            raise ValidationError("Last name cannot be empty", field="last_name")
        object.__setattr__(self, "_first_name", first_name.strip())
        object.__setattr__(self, "_last_name", last_name.strip())

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def full(self) -> str:
        return f"{self._first_name} {self._last_name}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FullName):
            return NotImplemented
        return self._first_name == other._first_name and self._last_name == other._last_name

    def __hash__(self) -> int:
        return hash((self._first_name, self._last_name))

    def __repr__(self) -> str:
        return f"FullName({self._first_name}, {self._last_name})"

    def __str__(self) -> str:
        return self.full

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("FullName is immutable")
