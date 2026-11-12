"""Text-driven queue notifications shared by UI pages.

NiceGUI already keeps a WebSocket connection per client; this hub lets the
server *push* a refresh signal the moment queue state changes instead of
polling the database from every browser.
"""

from __future__ import annotations

import asyncio


class RealtimeHub:
    """In-process pub/sub used to wake up connected pages."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[None]] = set()

    def subscribe(self) -> asyncio.Queue[None]:
        """Register a bounded queue that receives one token per publish()."""
        queue: asyncio.Queue[None] = asyncio.Queue(maxsize=1)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[None]) -> None:
        self._subscribers.discard(queue)

    def publish(self) -> None:
        """Wake every subscriber; a full queue already carries a pending signal."""
        for queue in tuple(self._subscribers):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                pass


hub = RealtimeHub()
