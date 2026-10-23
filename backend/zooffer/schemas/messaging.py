from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StartInquiryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_public_id: UUID
    message: str | None = Field(default=None, max_length=4000)


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str) -> str:
        cleaned = value.replace("\r\n", "\n").strip()
        if not cleaned:
            raise ValueError("Сообщение не может быть пустым")
        if any(ord(char) < 32 and char not in "\n\t" for char in cleaned):
            raise ValueError("Сообщение содержит недопустимые символы")
        return cleaned


class PublicCounterpartyView(BaseModel):
    """Only the public display name. Never add contacts or account identifiers."""

    display_name: str | None = None


class ConversationListingView(BaseModel):
    public_id: UUID
    slug: str
    title: str
    animal_name: str
    primary_photo_url: str | None = None


class MessageView(BaseModel):
    id: UUID
    body: str
    mine: bool
    edited_at: datetime | None = None
    created_at: datetime


class LastMessageView(BaseModel):
    body: str
    mine: bool
    created_at: datetime


class ConversationSummaryView(BaseModel):
    public_id: UUID
    conversation_type: str
    counterpart: PublicCounterpartyView
    listing: ConversationListingView | None = None
    last_message: LastMessageView | None = None
    unread_count: int = 0
    last_message_at: datetime | None = None
    updated_at: datetime
    blocked: bool = False


class ConversationListView(BaseModel):
    items: list[ConversationSummaryView]


class ConversationDetailView(BaseModel):
    conversation: ConversationSummaryView
    messages: list[MessageView]
    next_cursor: str | None = None
    has_more: bool = False


class MessagePageView(BaseModel):
    items: list[MessageView]
    next_cursor: str | None = None
    has_more: bool = False
