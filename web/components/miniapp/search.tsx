"use client";

import { useMemo, useState } from "react";

import { ListingCard } from "../listing-card";
import { SearchIcon } from "../icons";
import { api } from "@/lib/client";
import type { ListingPageData, Purpose } from "@/lib/types";

import { MiniEmpty, MiniError, MiniLoading, useMiniApi } from "./ui";

const purposes: { value: Purpose; label: string }[] = [
  { value: "sale", label: "Продажа" },
  { value: "mating", label: "Вязка" },
  { value: "breeding_pedigree", label: "Племенное" },
  { value: "adoption", label: "Пристройство" },
  { value: "rehoming", label: "Переустройство" },
];

const speciesOptions = [
  { value: "", label: "Все виды" },
  { value: "dog", label: "Собаки" },
  { value: "cat", label: "Кошки" },
  { value: "bird", label: "Птицы" },
  { value: "rodent", label: "Грызуны" },
  { value: "reptile", label: "Рептилии" },
  { value: "other", label: "Другие" },
];

interface Filters {
  q: string;
  purposes: string[];
  species: string;
  sex: string;
  sort: string;
}

const initialFilters: Filters = {
  q: "",
  purposes: [],
  species: "",
  sex: "",
  sort: "newest",
};

function buildQuery(filters: Filters, cursor?: string | null): string {
  const query = new URLSearchParams();
  if (filters.q.trim()) query.set("q", filters.q.trim());
  for (const purpose of filters.purposes) query.append("purpose", purpose);
  if (filters.species) query.set("species", filters.species);
  if (filters.sex) query.set("sex", filters.sex);
  query.set("sort", filters.sort);
  query.set("limit", "24");
  if (cursor) query.set("cursor", cursor);
  return `/api/v1/public/listings?${query.toString()}`;
}

export function MiniSearch() {
  const [draft, setDraft] = useState(initialFilters);
  const [filters, setFilters] = useState(initialFilters);
  const [extra, setExtra] = useState<ListingPageData["items"]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const path = useMemo(() => buildQuery(filters), [filters]);
  const { data, loading, error, reload } = useMiniApi<ListingPageData>(path);

  const apply = (next: Filters) => {
    setFilters(next);
    setDraft(next);
    setExtra([]);
    setCursor(null);
    setHasMore(false);
  };

  const togglePurpose = (purpose: string) => {
    const exists = draft.purposes.includes(purpose);
    apply({
      ...draft,
      purposes: exists
        ? draft.purposes.filter((item) => item !== purpose)
        : [...draft.purposes, purpose],
    });
  };

  const loadMore = async () => {
    if (!cursor || loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await api<ListingPageData>(buildQuery(filters, cursor));
      setExtra((current) => {
        const seen = new Set(current.map((item) => item.public_id));
        return [...current, ...page.items.filter((item) => !seen.has(item.public_id))];
      });
      setCursor(page.next_cursor);
      setHasMore(page.has_more);
    } finally {
      setLoadingMore(false);
    }
  };

  const items = [...(data?.items ?? []), ...extra];
  const nextCursor = cursor ?? data?.next_cursor ?? null;
  const canLoadMore = hasMore || Boolean(data?.has_more);

  return (
    <div className="tg-search">
      <header className="tg-page-head tg-page-head-tight">
        <div>
          <span className="eyebrow">Поиск</span>
          <h1>Найдите своего</h1>
          <p className="tg-lead">Живые объявления с проверенной модерацией.</p>
        </div>
      </header>

      <form
        className="tg-searchbar"
        onSubmit={(event) => {
          event.preventDefault();
          apply({ ...draft, q: draft.q });
        }}
        role="search"
      >
        <SearchIcon width={18} height={18} />
        <input
          value={draft.q}
          onChange={(event) => setDraft({ ...draft, q: event.target.value })}
          placeholder="Порода, имя, город"
          aria-label="Поиск объявлений"
          maxLength={80}
        />
        <button type="submit" className="tg-search-submit">
          Найти
        </button>
      </form>

      <div className="tg-chip-scroll" role="group" aria-label="Цель объявления">
        <button
          type="button"
          className={`tg-filter-chip${filters.purposes.length === 0 ? " active" : ""}`}
          onClick={() => apply({ ...draft, purposes: [] })}
        >
          Все
        </button>
        {purposes.map((item) => (
          <button
            key={item.value}
            type="button"
            className={`tg-filter-chip${filters.purposes.includes(item.value) ? " active" : ""}`}
            onClick={() => togglePurpose(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="tg-filter-row">
        <label>
          <span>Вид</span>
          <select
            className="select"
            value={draft.species}
            onChange={(event) => apply({ ...draft, species: event.target.value })}
          >
            {speciesOptions.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Пол</span>
          <select
            className="select"
            value={draft.sex}
            onChange={(event) => apply({ ...draft, sex: event.target.value })}
          >
            <option value="">Любой</option>
            <option value="male">Мальчик</option>
            <option value="female">Девочка</option>
          </select>
        </label>
        <label>
          <span>Сортировка</span>
          <select
            className="select"
            value={draft.sort}
            onChange={(event) => apply({ ...draft, sort: event.target.value })}
          >
            <option value="newest">Сначала новые</option>
            <option value="price_asc">Цена по возрастанию</option>
            <option value="price_desc">Цена по убыванию</option>
          </select>
        </label>
      </div>

      {loading && !items.length && <MiniLoading label="Ищем объявления…" />}
      {error && !items.length && <MiniError message={error} onRetry={reload} />}
      {!loading && !error && !items.length && (
        <MiniEmpty
          title="Ничего не нашлось"
          text="Попробуйте убрать один из фильтров или изменить запрос."
          href="/tg"
          action="Вернуться к подбору"
        />
      )}

      {items.length > 0 && (
        <>
          <p className="tg-result-count">{items.length} объявлений</p>
          <div className="tg-listing-grid">
            {items.map((listing, index) => (
              <ListingCard
                key={listing.public_id}
                listing={listing}
                basePath="/tg/listing"
                priority={index < 2}
                compact
              />
            ))}
          </div>
          {canLoadMore && nextCursor && (
            <button
              type="button"
              className="btn btn-secondary btn-sm tg-load-more"
              onClick={() => void loadMore()}
              disabled={loadingMore}
            >
              {loadingMore ? "Загружаем…" : "Показать ещё"}
            </button>
          )}
        </>
      )}
    </div>
  );
}
