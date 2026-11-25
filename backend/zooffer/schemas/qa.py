from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionCreateRequest(StrictModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(default="", max_length=8000)
    tags: list[str] = Field(default_factory=list)


class AnswerCreateRequest(StrictModel):
    body: str = Field(min_length=1, max_length=8000)


class PublicQAOwnerView(BaseModel):
    display_name: str | None = None


class PublicAnswerView(BaseModel):
    public_id: UUID
    body: str
    is_best: bool = False
    vet_marked: bool = False
    created_at: datetime
    author: PublicQAOwnerView


class PublicQuestionView(BaseModel):
    public_id: UUID
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    status: str
    best_answer_id: UUID | None = None
    created_at: datetime
    author: PublicQAOwnerView
    answers: list[PublicAnswerView] = Field(default_factory=list)


class QuestionOwnerView(BaseModel):
    public_id: UUID
    title: str
    body: str
    tags: list[str] = Field(default_factory=list)
    status: str
    created_at: datetime
    updated_at: datetime


class QuestionListResponse(BaseModel):
    items: list[PublicQuestionView]
    meta: dict[str, Any] = Field(default_factory=dict)


class AnswerView(BaseModel):
    public_id: UUID
    body: str
    is_best: bool = False
    vet_marked: bool = False
    created_at: datetime
    author: PublicQAOwnerView
