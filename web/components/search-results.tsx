import Link from "next/link";

import { ListingCard } from "./listing-card";
import { SearchFilters, type FilterValues } from "./search-filters";
import { ArrowIcon, PawIcon, SearchIcon } from "./icons";
import { searchListings } from "@/lib/data";
import type { Dictionaries, ListingPageData, Purpose } from "@/lib/types";

type RawParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

function all(value: string | string[] | undefined): string[] {
  if (Array.isArray(value)) return value.filter(Boolean);
  return value ? [value] : [];
}

const headingByPurpose: Record<string, string> = {
  sale: "Животные в продаже",
  mating: "Вязка",
  breeding_pedigree: "Племенное разведение",
  adoption: "Пристройство",
};

export async function SearchResults({
  params,
  dictionaries,
  basePath = "/search",
  fixedPurposes,
}: {
  params: RawParams;
  dictionaries: Dictionaries | null;
  basePath?: string;
  fixedPurposes?: Purpose[];
}) {
  const purposes = fixedPurposes ?? all(params.purpose);
  const query: Record<string, unknown> = {
    q: first(params.q) || undefined,
    purpose: purposes.length ? purposes : undefined,
    species: first(params.species) || undefined,
    sex: first(params.sex) || undefined,
    min_age: first(params.min_age) || undefined,
    max_age: first(params.max_age) || undefined,
    size: first(params.size) || undefined,
    city_id: first(params.city_id) || undefined,
    price_min: first(params.price_min) || undefined,
    price_max: first(params.price_max) || undefined,
    has_pedigree: first(params.has_pedigree) || undefined,
    vaccinated: first(params.vaccinated) || undefined,
    with_photos: first(params.with_photos) || undefined,
    sort: first(params.sort) || "newest",
    cursor: first(params.cursor) || undefined,
    limit: 24,
  };
  const data: ListingPageData | null = await searchListings(query);

  const initial: FilterValues = {
    q: first(params.q),
    purposes,
    species: first(params.species),
    sex: first(params.sex),
    minAge: first(params.min_age),
    maxAge: first(params.max_age),
    size: first(params.size),
    cityId: first(params.city_id),
    priceMin: first(params.price_min) ? String(Number(first(params.price_min)) / 100) : "",
    priceMax: first(params.price_max) ? String(Number(first(params.price_max)) / 100) : "",
    pedigree: first(params.has_pedigree),
    vaccinated: first(params.vaccinated),
    photos: first(params.with_photos) === "true",
    sort: first(params.sort) || "newest",
  };

  const heading =
    fixedPurposes?.length === 1
      ? (headingByPurpose[fixedPurposes[0]] ?? "Поиск животных")
      : initial.q
        ? `Результаты по запросу «${initial.q}»`
        : "Все животные";

  const nextParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (key === "cursor" || value === undefined) continue;
    if (Array.isArray(value)) {
      for (const item of value) nextParams.append(key, item);
    } else {
      nextParams.set(key, value);
    }
  }
  if (fixedPurposes) {
    nextParams.delete("purpose");
    for (const purpose of fixedPurposes) nextParams.append("purpose", purpose);
  }

  return (
    <div className="page page-tight">
      <div className="container">
        <div className="search-page-head">
          <div>
            <span className="eyebrow">Поиск</span>
            <h1>{heading}</h1>
            <p className="muted">
              {data?.items.length
                ? "Объявления обновляются в реальном времени. Уточните фильтры, чтобы найти ближе к вам."
                : "Показываем только живые и опубликованные объявления."}
            </p>
          </div>
          <div className="search-head-actions">
            <form action={basePath} className="search-mini">
              <label htmlFor="search-q" className="sr-only">
                Поиск по объявлениям
              </label>
              <SearchIcon width={17} height={17} />
              <input
                id="search-q"
                name="q"
                defaultValue={initial.q}
                placeholder="Порода, имя, город"
                autoComplete="off"
              />
              <button type="submit" className="btn btn-primary btn-sm">
                Найти
              </button>
            </form>
          </div>
        </div>

        <div className="search-layout">
          <SearchFilters dictionaries={dictionaries} initial={initial} basePath={basePath} />
          <div className="search-results">
            {data && data.items.length > 0 ? (
              <>
                <div className="result-bar">
                  <span className="muted">
                    {data.items.length} на этой странице
                    {data.has_more ? ", есть ещё" : ""}
                  </span>
                  <span className="chip chip-brand">Только актуальные</span>
                </div>
                <div className="listing-grid">
                  {data.items.map((listing, index) => (
                    <ListingCard key={listing.public_id} listing={listing} priority={index < 3} />
                  ))}
                </div>
                {data.has_more && data.next_cursor && (
                  <div className="load-more">
                    <Link
                      href={`${basePath}?${nextParams.toString()}&cursor=${encodeURIComponent(data.next_cursor)}`}
                      className="btn btn-secondary"
                    >
                      Показать ещё <ArrowIcon />
                    </Link>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <PawIcon width={46} height={46} />
                <h2>{data ? "Ничего не нашлось" : "Не удалось загрузить объявления"}</h2>
                <p>
                  {data
                    ? "Попробуйте убрать часть фильтров или изменить запрос. Новые объявления появляются каждый день."
                    : "Проверьте соединение и попробуйте обновить страницу. Ваши фильтры сохранены в адресе."}
                </p>
                <div className="btn-row">
                  <Link href={basePath} className="btn btn-secondary">
                    Сбросить фильтры
                  </Link>
                  <Link href="/discovery" className="btn btn-primary">
                    Перейти к подбору
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
