from __future__ import annotations

from typing import Protocol

from src.domain.events import DomainEvent


class EventHandler(Protocol):
    """Protocol for domain event handlers."""

    async def handle(self, event: DomainEvent) -> None: ...
