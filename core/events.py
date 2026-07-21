"""
Event-driven system.
All major actions emit events that listeners handle asynchronously.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """All event types in the system."""
    # Payment events
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"

    # Order events
    ORDER_CREATED = "order_created"
    ORDER_DELIVERED = "order_delivered"
    ORDER_FAILED = "order_failed"

    # Gift events
    GIFT_LINK_OPENED = "gift_link_opened"
    GIFT_LINK_DELIVERED = "gift_link_delivered"

    # Refund events
    REFUND_REQUESTED = "refund_requested"
    REFUND_APPROVED = "refund_approved"
    REFUND_COMPLETED = "refund_completed"
    REFUND_REJECTED = "refund_rejected"

    # User events
    USER_REGISTERED = "user_registered"

    # Admin events
    BROADCAST_SENT = "broadcast_sent"


@dataclass
class Event:
    """Event data container."""
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=asyncio.get_event_loop().time)


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventDispatcher:
    """Centralized event dispatcher for the application."""

    def __init__(self):
        self._listeners: dict[EventType, list[EventHandler]] = {}
        self._instance = None

    def register(self, event_type: EventType, handler: EventHandler) -> None:
        """Register an event handler."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")

    async def emit(self, event: Event) -> None:
        """Emit an event to all registered listeners."""
        handlers = self._listeners.get(event.type, [])
        if not handlers:
            logger.debug(f"No handlers for event: {event.type.value}")
            return

        logger.info(f"Emitting event: {event.type.value}")
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type.value}: {e}", exc_info=True)

    async def emit_sync(self, event: Event) -> None:
        """Emit an event (synchronous wrapper for non-async contexts)."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(self.emit(event))
        else:
            loop.run_until_complete(self.emit(event))


# Global dispatcher instance
dispatcher = EventDispatcher()
