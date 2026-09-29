"""سیستم رویداد درون‌فرایندی برای به‌روزرسانی بلادرنگ UI هنگام محاسبه مسیر."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Event", "EventBus", "ROUTE_QUEUED", "ROUTE_RUNNING", "ROUTE_SUCCEEDED", "ROUTE_FAILED"]

ROUTE_QUEUED = "route.queued"
ROUTE_RUNNING = "route.running"
ROUTE_SUCCEEDED = "route.succeeded"
ROUTE_FAILED = "route.failed"


@dataclass(frozen=True)
class Event:
    """یک رویداد با نوع و بار داده (payload) JSON‌پذیر."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """گذرگاه publish/subscribe ایمن در برابر چندنخی.

    خطای یک subscriber نباید محاسبه مسیر یا سایر subscriberها را مختل کند؛
    آن خطا نادیده گرفته و در ``errors`` ثبت می‌شود.
    """

    def __init__(self) -> None:
        self._subs: list[tuple[str | None, Callable[[Event], None]]] = []
        self._lock = threading.Lock()
        self.errors: list[Exception] = []

    def subscribe(
        self, callback: Callable[[Event], None], event_type: str | None = None
    ) -> Callable[[], None]:
        """اشتراک؛ ``event_type=None`` یعنی همه رویدادها. تابع لغو اشتراک برمی‌گرداند."""
        entry = (event_type, callback)
        with self._lock:
            self._subs.append(entry)

        def unsubscribe() -> None:
            with self._lock:
                if entry in self._subs:
                    self._subs.remove(entry)

        return unsubscribe

    def publish(self, event: Event) -> None:
        with self._lock:
            targets = [cb for t, cb in self._subs if t is None or t == event.type]
        for cb in targets:
            try:
                cb(event)
            except Exception as exc:  # noqa: BLE001 - ایزوله‌سازی subscriberها
                self.errors.append(exc)
