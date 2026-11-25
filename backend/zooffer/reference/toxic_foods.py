from __future__ import annotations

# Static reference data: "can my pet eat this?"
# Species-aware. Values: safe | caution | toxic.
TOXIC_FOODS: list[dict[str, str]] = [
    {
        "name": "Шоколад",
        "species": "dog",
        "verdict": "toxic",
        "note": "Теобромин токсичен для собак.",
    },
    {
        "name": "Шоколад",
        "species": "cat",
        "verdict": "toxic",
        "note": "Теобромин токсичен для кошек.",
    },
    {"name": "Лук и чеснок", "species": "dog", "verdict": "toxic", "note": "Разрушают эритроциты."},
    {
        "name": "Лук и чеснок",
        "species": "cat",
        "verdict": "toxic",
        "note": "Особенно опасны для кошек.",
    },
    {
        "name": "Виноград и изюм",
        "species": "dog",
        "verdict": "toxic",
        "note": "Риск почечной недостаточности.",
    },
    {
        "name": "Ксилит",
        "species": "dog",
        "verdict": "toxic",
        "note": "Резкое падение сахара, печёночная недостаточность.",
    },
    {
        "name": "Авокадо",
        "species": "dog",
        "verdict": "caution",
        "note": "Персин токсичен в больших количествах.",
    },
    {
        "name": "Авокадо",
        "species": "cat",
        "verdict": "caution",
        "note": "Персин токсичен в больших количествах.",
    },
    {
        "name": "Молоко",
        "species": "cat",
        "verdict": "caution",
        "note": "У взрослых кошек часто непереносимость лактозы.",
    },
    {
        "name": "Кости (варёные)",
        "species": "dog",
        "verdict": "caution",
        "note": "Риск осколков и непроходимости.",
    },
    {
        "name": "Морковь",
        "species": "dog",
        "verdict": "safe",
        "note": "Полезна в умеренных количествах.",
    },
    {"name": "Морковь", "species": "cat", "verdict": "safe", "note": "Можно давать как лакомство."},
    {"name": "Яблоко (без семян)", "species": "dog", "verdict": "safe", "note": "Удалите семена."},
    {"name": "Яблоко (без семян)", "species": "cat", "verdict": "safe", "note": "Удалите семена."},
    {
        "name": "Арахисовое масло (без ксилита)",
        "species": "dog",
        "verdict": "safe",
        "note": "Проверьте состав на ксилит.",
    },
]


def search(query: str, species: str | None = None) -> list[dict[str, str]]:
    q = (query or "").strip().lower()
    result = []
    for item in TOXIC_FOODS:
        if species and item["species"] != species:
            continue
        if q and q not in item["name"].lower():
            continue
        result.append(item)
    return result
