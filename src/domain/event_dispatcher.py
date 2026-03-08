from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Type

from src.domain.events import DomainEvent
from src.domain.interfaces.event_handler import EventHandler


class DomainEventDispatcher:
    """Collects and dispatches domain events to registered handlers.

    Handlers are registered per event type. When dispatch() is called,
    each event is sent to all handlers registered for its type, plus
    any handlers registered for the base DomainEvent (catch-all).
    """

    def __init__(self) -> None:
        self._handlers: Dict[Type[DomainEvent], List[EventHandler]] = defaultdict(list)

    def register(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    async def dispatch(self, events: List[DomainEvent]) -> None:
        for event in events:
            event_type = type(event)
            # Handlers for the specific event type
            for handler in self._handlers.get(event_type, []):
                await handler.handle(event)
            # Catch-all handlers registered on base DomainEvent
            if event_type is not DomainEvent:
                for handler in self._handlers.get(DomainEvent, []):
                    await handler.handle(event)
