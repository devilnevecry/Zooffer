from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.core.errors import ForbiddenError
from zooffer.schemas.qa import (
    AnswerCreateRequest,
    PublicQuestionView,
    QuestionCreateRequest,
    QuestionListResponse,
    QuestionOwnerView,
)
from zooffer.services import qa_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.post("/questions", status_code=201)
async def create_question(payload: QuestionCreateRequest, auth: CurrentAuth, db: DbSession) -> dict:
    user = auth.user
    q = await qa_service.create_question(db, user, payload)
    return QuestionOwnerView(**await qa_service.question_to_owner(db, q)).model_dump()


@router.get("/questions")
async def list_questions(
    db: DbSession,
    tag: str | None = Query(default=None),
    status: str = Query(default="open"),
    limit: int = Query(default=50, le=200),
) -> QuestionListResponse:
    qs = await qa_service.list_questions(db, tag=tag, status=status, limit=limit)
    items = [PublicQuestionView(**await qa_service.question_to_public(db, q)) for q in qs]
    return QuestionListResponse(items=items, meta={"total": len(items)})


@router.get("/questions/{public_id}")
async def get_question(public_id: uuid.UUID, db: DbSession) -> PublicQuestionView:
    q = await qa_service.get_question(db, public_id)
    return PublicQuestionView(**await qa_service.question_to_public(db, q))


@router.post("/questions/{public_id}/answers", status_code=201)
async def add_answer(
    public_id: uuid.UUID, payload: AnswerCreateRequest, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    a = await qa_service.add_answer(db, user, public_id, payload)
    return {
        "public_id": a.public_id,
        "body": a.body,
        "is_best": a.is_best,
        "vet_marked": a.vet_marked,
        "created_at": a.created_at,
        "author": {"display_name": await qa_service._owner_name(db, a.author_id)},
    }


@router.post("/questions/{public_id}/answers/{answer_public_id}/best")
async def mark_best(
    public_id: uuid.UUID, answer_public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    q = await qa_service.mark_best(db, user, public_id, answer_public_id)
    return QuestionOwnerView(**await qa_service.question_to_owner(db, q)).model_dump()


@router.post("/questions/{public_id}/answers/{answer_public_id}/vet-mark")
async def vet_mark(
    public_id: uuid.UUID, answer_public_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> dict:
    user = auth.user
    if getattr(user, "role", None) not in {"moderator", "admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    a = await qa_service.vet_mark(db, user, public_id, answer_public_id)
    return {
        "public_id": a.public_id,
        "body": a.body,
        "is_best": a.is_best,
        "vet_marked": a.vet_marked,
        "created_at": a.created_at,
        "author": {"display_name": await qa_service._owner_name(db, a.author_id)},
    }
