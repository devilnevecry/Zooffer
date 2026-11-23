from __future__ import annotations

from . import chats, discovery, fallback, favorites, listings, menu, payments, start, support

ROUTERS = (
    start.router,
    menu.router,
    payments.router,
    discovery.router,
    favorites.router,
    chats.router,
    listings.router,
    support.router,
    fallback.router,
)

__all__ = ["ROUTERS"]
