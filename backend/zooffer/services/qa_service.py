from __future__ import annotations

import uuid

from sqlalchemy import select, update

from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import Answer, Profile, Question


async def _get_question(db, public_id):
    q = await db.scalar(select(Question).where(Question.public_id == public_id))
    if q is None:
        raise NotFoundError("Вопрос не найден", code="question_not_found")
    return q


async def _owner_name(db, user_id):
    profile = await db.get(Profile, user_id)
    if profile is None:
        return None
    first = profile.public_first_name
    last = profile.public_last_name
    if first and last:
        return f"{first} {last}"
    return first or last


async def create_question(db, user, payload) -> Question:
    q = Question(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        author_id=user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        tags=payload.tags,
        status="open",
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


async def get_question(db, public_id):
    return await _get_question(db, public_id)


async def list_questions(db, *, tag=None, status="open", limit=50):
    q = select(Question).where(Question.status == status)
    rows = (await db.scalars(q)).all()
    if tag:
        rows = [r for r in rows if tag in (r.tags or [])]
    rows = sorted(rows, key=lambda r: r.created_at, reverse=True)
    return list(rows[:limit])


async def add_answer(db, user, question_public_id, payload) -> Answer:
    question = await _get_question(db, question_public_id)
    if question.status != "open":
        raise ValidationAppError("Вопрос закрыт", code="question_closed")
    a = Answer(
        id=uuid.uuid4(),
        public_id=uuid.uuid4(),
        question_id=question.id,
        author_id=user.id,
        body=payload.body.strip(),
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return a


async def mark_best(db, user, question_public_id, answer_public_id) -> Question:
    question = await _get_question(db, question_public_id)
    if question.author_id != user.id:
        raise ForbiddenError("Нет прав", code="forbidden")
    answer = await db.scalar(
        select(Answer).where(
            Answer.public_id == answer_public_id, Answer.question_id == question.id
        )
    )
    if answer is None:
        raise NotFoundError("Ответ не найден", code="answer_not_found")
    await db.execute(update(Answer).where(Answer.question_id == question.id).values(is_best=False))
    answer.is_best = True
    question.best_answer_id = answer.id
    question.status = "closed"
    await db.commit()
    await db.refresh(question)
    return question


async def vet_mark(db, user, question_public_id, answer_public_id) -> Answer:
    if getattr(user, "role", None) not in {"moderator", "admin", "superadmin"}:
        raise ForbiddenError("Недостаточно прав", code="permission_denied")
    question = await _get_question(db, question_public_id)
    answer = await db.scalar(
        select(Answer).where(
            Answer.public_id == answer_public_id, Answer.question_id == question.id
        )
    )
    if answer is None:
        raise NotFoundError("Ответ не найден", code="answer_not_found")
    answer.vet_marked = True
    await db.commit()
    await db.refresh(answer)
    return answer


async def list_answers(db, question_public_id) -> list[Answer]:
    question = await _get_question(db, question_public_id)
    rows = (
        await db.scalars(
            select(Answer).where(Answer.question_id == question.id).order_by(Answer.created_at)
        )
    ).all()
    return list(rows)


async def question_to_public(db, q) -> dict:
    answers = await list_answers(db, q.public_id)
    answer_views = []
    for a in answers:
        answer_views.append(
            {
                "public_id": a.public_id,
                "body": a.body,
                "is_best": a.is_best,
                "vet_marked": a.vet_marked,
                "created_at": a.created_at,
                "author": {"display_name": await _owner_name(db, a.author_id)},
            }
        )
    return {
        "public_id": q.public_id,
        "title": q.title,
        "body": q.body,
        "tags": q.tags or [],
        "status": q.status,
        "best_answer_id": q.best_answer_id,
        "created_at": q.created_at,
        "author": {"display_name": await _owner_name(db, q.author_id)},
        "answers": answer_views,
    }


async def question_to_owner(db, q) -> dict:
    return {
        "public_id": q.public_id,
        "title": q.title,
        "body": q.body,
        "tags": q.tags or [],
        "status": q.status,
        "created_at": q.created_at,
        "updated_at": q.updated_at,
    }
