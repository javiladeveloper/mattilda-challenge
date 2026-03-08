from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from src.domain.events import DomainEvent, SchoolDeactivated
from src.domain.exceptions import BusinessRuleError, ValidationError
from src.domain.value_objects import EmailAddress


class School:
    """School domain entity."""

    def __init__(
        self,
        name: str,
        address: str = "",
        phone: str = "",
        email: str | None = None,
        id: UUID | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        if not name or not name.strip():
            raise ValidationError("School name cannot be empty", field="name")
        if email:
            EmailAddress(email)

        self.id = id or uuid4()
        self.name = name.strip()
        self.address = address or ""
        self.phone = phone or ""
        self.email = email
        self.is_active = is_active
        self._events: List[DomainEvent] = []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    @property
    def domain_events(self) -> List[DomainEvent]:
        return list(self._events)

    def clear_events(self) -> None:
        self._events.clear()

    def deactivate(self) -> None:
        if not self.is_active:
            raise BusinessRuleError("School is already inactive")
        self.is_active = False
        self.updated_at = datetime.utcnow()
        self._events.append(SchoolDeactivated(school_id=self.id))

    def update(self, **kwargs: object) -> None:
        allowed = {"name", "address", "phone", "email", "is_active"}
        for key, value in kwargs.items():
            if key not in allowed:
                raise ValidationError(f"Cannot update field: {key}", field=key)
            if key == "email" and value:
                EmailAddress(value)
            setattr(self, key, value)
        self.updated_at = datetime.utcnow()
