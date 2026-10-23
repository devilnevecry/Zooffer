from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReportTargetType = Literal["listing", "animal", "message", "user"]
ReportReason = Literal["spam", "scam", "cruelty", "prohibited", "contacts", "other"]


class ReportCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: ReportTargetType
    target_public_id: UUID
    reason: ReportReason
    details: str | None = Field(default=None, max_length=1000)

    @field_validator("details")
    @classmethod
    def clean_details(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.replace("\r\n", "\n").strip()
        return cleaned or None


class ReportView(BaseModel):
    id: UUID
    target_type: str
    reason: str
    status: str
    created_at: datetime
