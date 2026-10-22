from __future__ import annotations

import uuid

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import func, select

from zooffer.api.deps import CurrentAuth, DbSession
from zooffer.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from zooffer.db.models import AnimalDocument, AnimalPhoto
from zooffer.schemas.listing import (
    AnimalCreateRequest,
    AnimalPhotoOwnerView,
    AnimalUpdateRequest,
)
from zooffer.services import listing_service
from zooffer.services.media import (
    MAX_IMAGES_PER_ANIMAL,
    get_storage,
    media_url,
    process_and_store_image,
    thumb_key_for,
)

router = APIRouter(prefix="/animals", tags=["animals"])


def _photo_view(photo: AnimalPhoto) -> AnimalPhotoOwnerView:
    return AnimalPhotoOwnerView(
        id=photo.id,
        url=media_url(photo.storage_key),
        thumb_url=media_url(thumb_key_for(photo.storage_key)),
        width=photo.width,
        height=photo.height,
        position=photo.position,
        is_primary=photo.is_primary,
        alt_text=photo.alt_text,
    )


async def _animal_payload(db: DbSession, animal_id, owner_id) -> dict:  # type: ignore[no-untyped-def]
    animal = await listing_service.get_animal_for_owner(db, owner_id, animal_id)
    photos = (
        await db.scalars(
            select(AnimalPhoto)
            .where(AnimalPhoto.animal_id == animal.id)
            .order_by(AnimalPhoto.position)
        )
    ).all()
    return {
        "public_id": animal.public_id,
        "name": animal.name,
        "species": animal.species,
        "breed": animal.breed_text,
        "sex": animal.sex,
        "birth_date": animal.birth_date,
        "colour": animal.colour,
        "size": animal.size,
        "has_pedigree": animal.has_pedigree,
        "pedigree_registry": animal.pedigree_registry,
        "pedigree_number": animal.pedigree_number,
        "vaccinated": animal.vaccinated,
        "health_notes": animal.health_notes,
        "description": animal.description,
        "archived_at": animal.archived_at,
        "photos": [_photo_view(p).model_dump() for p in photos],
    }


@router.post("", status_code=201)
async def create_animal(
    payload: AnimalCreateRequest,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.create_animal(db, user, payload)
    return await _animal_payload(db, animal.public_id, user.id)


@router.get("")
async def list_animals(auth: CurrentAuth, db: DbSession) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animals = await listing_service.list_owned_animals(db, user.id)
    return {
        "items": [await _animal_payload(db, a.public_id, user.id) for a in animals],
    }


@router.patch("/{public_id}")
async def update_animal(
    public_id: uuid.UUID,
    payload: AnimalUpdateRequest,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    await listing_service.update_animal(db, user, public_id, payload)
    return await _animal_payload(db, public_id, user.id)


@router.post("/{public_id}/photos", status_code=201)
async def upload_photo(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
    file: UploadFile = File(...),  # noqa: B008
) -> AnimalPhotoOwnerView:
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    count = await db.scalar(
        select(func.count()).select_from(AnimalPhoto).where(AnimalPhoto.animal_id == animal.id)
    )
    if int(count or 0) >= MAX_IMAGES_PER_ANIMAL:
        raise ValidationAppError("Можно загрузить не более 10 фотографий", code="photo_limit")
    content = await file.read()
    processed = await process_and_store_image(content)
    position = int(count or 0)
    photo = AnimalPhoto(
        id=uuid.uuid4(),
        animal_id=animal.id,
        storage_key=processed.full_key,
        position=position,
        width=processed.width,
        height=processed.height,
        content_hash=processed.content_hash,
        is_primary=position == 0,
        alt_text=animal.name,
    )
    db.add(photo)
    await db.commit()
    return _photo_view(photo)


@router.delete("/{public_id}/photos/{photo_id}")
async def delete_photo(
    public_id: uuid.UUID,
    photo_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    photo = await db.get(AnimalPhoto, photo_id)
    if photo is None or photo.animal_id != animal.id:
        raise NotFoundError("Фотография не найдена", code="photo_not_found")
    await db.delete(photo)
    remaining = (
        await db.scalars(
            select(AnimalPhoto)
            .where(AnimalPhoto.animal_id == animal.id)
            .order_by(AnimalPhoto.position)
        )
    ).all()
    for index, item in enumerate(remaining):
        item.position = index
    if remaining and not any(item.is_primary for item in remaining):
        remaining[0].is_primary = True
    await db.commit()
    return {"ok": True}


@router.post("/{public_id}/photos/{photo_id}/primary")
async def set_primary_photo(
    public_id: uuid.UUID,
    photo_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    photo = await db.get(AnimalPhoto, photo_id)
    if photo is None or photo.animal_id != animal.id:
        raise NotFoundError("Фотография не найдена", code="photo_not_found")
    await db.execute(
        AnimalPhoto.__table__.update()
        .where(AnimalPhoto.animal_id == animal.id)
        .values(is_primary=False)
    )
    photo.is_primary = True
    await db.commit()
    return {"ok": True}


@router.put("/{public_id}/photos/order")
async def reorder_photos(
    public_id: uuid.UUID,
    order: list[uuid.UUID],
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    photos = (await db.scalars(select(AnimalPhoto).where(AnimalPhoto.animal_id == animal.id))).all()
    by_id = {p.id: p for p in photos}
    if set(order) != set(by_id):
        raise ValidationAppError("Некорректный порядок фотографий", code="invalid_order")
    for index, photo_id in enumerate(order):
        by_id[photo_id].position = index
    await db.commit()
    return {"ok": True}


@router.post("/{public_id}/documents", status_code=201)
async def upload_document(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
    file: UploadFile = File(...),  # noqa: B008
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    content = await file.read()
    if not content or len(content) > 10 * 1024 * 1024:
        raise ValidationAppError("Документ должен быть не больше 10 МБ", code="invalid_document")
    is_pdf = content[:5] == b"%PDF-"
    is_image = content[:3] == b"\xff\xd8\xff" or content[:8] == b"\x89PNG\r\n\x1a\n"
    if not (is_pdf or is_image):
        raise ValidationAppError("Загрузите PDF или изображение документа", code="invalid_document")
    content_type = "application/pdf" if is_pdf else "image/jpeg"
    key = f"documents/{uuid.uuid4().hex}.{'pdf' if is_pdf else 'jpg'}"
    await get_storage().save(key, content, content_type)
    document = AnimalDocument(
        id=uuid.uuid4(),
        animal_id=animal.id,
        owner_id=user.id,
        storage_key=key,
        document_type="pedigree",
        status="private",
        content_type=content_type,
    )
    db.add(document)
    await db.commit()
    # Never return the storage key or a URL: documents are private by default.
    return {
        "id": str(document.id),
        "document_type": document.document_type,
        "status": document.status,
        "content_type": document.content_type,
    }


@router.get("/{public_id}/documents")
async def list_documents(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    docs = (
        await db.scalars(select(AnimalDocument).where(AnimalDocument.animal_id == animal.id))
    ).all()
    return {
        "items": [
            {
                "id": str(d.id),
                "document_type": d.document_type,
                "status": d.status,
                "content_type": d.content_type,
                "created_at": d.created_at,
            }
            for d in docs
        ]
    }


@router.delete("/{public_id}")
async def archive_animal(
    public_id: uuid.UUID,
    auth: CurrentAuth,
    db: DbSession,
) -> dict:  # type: ignore[valid-type]
    from zooffer.core.utils import utcnow
    from zooffer.db.models import Listing

    user = auth.user  # type: ignore[attr-defined]
    animal = await listing_service.get_animal_for_owner(db, user.id, public_id)
    published = await db.scalar(
        select(Listing.id).where(Listing.animal_id == animal.id, Listing.status == "published")
    )
    if published:
        raise ForbiddenError("Сначала снимите объявление с публикации", code="listing_published")
    animal.archived_at = utcnow()
    await db.commit()
    return {"ok": True}
