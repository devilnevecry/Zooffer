from __future__ import annotations

from fastapi import APIRouter, Query

from zooffer.reference.toxic_foods import search

router = APIRouter(prefix="/reference", tags=["reference"])


@router.get("/toxic-foods")
async def toxic_foods(
    q: str | None = Query(default=None),
    species: str | None = Query(default=None),
) -> dict:
    items = search(q or "", species)
    return {"items": items}
