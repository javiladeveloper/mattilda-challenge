from __future__ import annotations

from datetime import date, datetime
from typing import List
from uuid import UUID, uuid4

from src.domain.events import DomainEvent, StudentDeactivated
from src.domain.exceptions import BusinessRuleError, ValidationError
from src.domain.value_objects import EmailAddress, FullName


class Student:
    """Student domain entity."""

    def __init__(
        self,
        first_name: str,
        last_name: str,
        school_id: UUID,
        email: str | None = None,
        grade: str = "",
        id: UUID | None = None,
        is_active: bool = True,
        enrolled_at: date | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        self._name = FullName(first_name, last_name)
        if email:
            EmailAddress(email)

        self.id = id or uuid4()
        self.school_id = school_id
        self.email = email
        self.grade = grade or ""
        self.is_active = is_active
        self._events: List[DomainEvent] = []
        self.enrolled_at = enrolled_at or date.today()
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    @property
    def first_name(self) -> str:
        return self._name.first_name

    @property
    def last_name(self) -> str:
        return self._name.last_name

    @property
    def full_name(self) -> str:
        return self._name.full

    @property
    def name(self) -> FullName:
        return self._name

    @property
    def domain_events(self) -> List[DomainEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    def deactivate(self) -> None:
        if not self.is_active:
            raise BusinessRuleError("Student is already inactive")
        self.is_active = False
        self.updated_at = datetime.utcnow()
        self._events.append(StudentDeactivated(
            student_id=self.id,
            school_id=self.school_id,
        ))

    def update(self, **kwargs: object) -> None:
        allowed = {"first_name", "last_name", "email", "school_id", "grade", "is_active"}
        for key, value in kwargs.items():
            if key not in allowed:
                raise ValidationError(f"Cannot update field: {key}", field=key)

        if "email" in kwargs and kwargs["email"]:
            EmailAddress(kwargs["email"])

        fn = kwargs.get("first_name", self.first_name)
        ln = kwargs.get("last_name", self.last_name)
        if "first_name" in kwargs or "last_name" in kwargs:
            self._name = FullName(fn, ln)

        for key in ("email", "school_id", "grade", "is_active"):
            if key in kwargs:
                setattr(self, key, kwargs[key])

        self.updated_at = datetime.utcnow()
