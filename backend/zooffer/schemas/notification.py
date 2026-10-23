from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class NotificationView(BaseModel):
    id: UUID
    category: str
    title: str
    body: str
    data: dict[str, Any] | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationListView(BaseModel):
    items: list[NotificationView]
    unread_count: int


class UnreadCountView(BaseModel):
    unread_count: int
