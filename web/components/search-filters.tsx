"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { FilterIcon, SearchIcon } from "./icons";
import type { Dictionaries, Purpose } from "@/lib/types";

const purposes: { value: Purpose; label: string }[] = [
  { value: "sale", label: "Продажа" },
  { value: "mating", label: "Вязка" },
  { value: "breeding_pedigree", label: "Племенное разведение" },
  { value: "adoption", label: "Пристройство" },
  { value: "rehoming", label: "Переустройство" },
];

const species = [
  { value: "dog", label: "Собака" },
  { value: "cat", label: "Кошка" },
  { value: "bird", label: "Птица" },
  { value: "rodent", label: "Грызун" },
  { value: "reptile", label: "Рептилия" },
  { value: "other", label: "Другое" },
];

export interface FilterValues {
  q: string;
  purposes: string[];
  species: string;
  sex: string;
  minAge: string;
  maxAge: string;
  size: string;
  cityId: string;
  priceMin: string;
  priceMax: string;
  pedigree: string;
  vaccinated: string;
  photos: boolean;
  sort: string;
}

export function SearchFilters({
  dictionaries,
  initial,
  basePath = "/search",
}: {
  dictionaries: Dictionaries | null;
  initial: FilterValues;
  basePath?: string;
}) {
  const router = useRouter();
  const [values, setValues] = useState(initial);
  const [open, setOpen] = useState(false);

  const set = <K extends keyof FilterValues>(key: K, value: FilterValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));

  const togglePurpose = (purpose: string) => {
    setValues((current) => {
      const exists = current.purposes.includes(purpose);
      return {
        ...current,
        purposes: exists
          ? current.purposes.filter((item) => item !== purpose)
          : [...current.purposes, purpose],
      };
    });
  };

  const apply = (event: React.FormEvent) => {
    event.preventDefault();
    const query = new URLSearchParams();
    if (values.q.trim()) query.set("q", values.q.trim());
    for (const purpose of values.purposes) query.append("purpose", purpose);
    if (values.species) query.set("species", values.species);
    if (values.sex) query.set("sex", values.sex);
    if (values.minAge) query.set("min_age", values.minAge);
    if (values.maxAge) query.set("max_age", values.maxAge);
    if (values.size) query.set("size", values.size);
    if (values.cityId) query.set("city_id", values.cityId);
    if (values.priceMin) query.set("price_min", String(Number(values.priceMin) * 100));
    if (values.priceMax) query.set("price_max", String(Number(values.priceMax) * 100));
    if (values.pedigree) query.set("has_pedigree", values.pedigree);
    if (values.vaccinated) query.set("vaccinated", values.vaccinated);
    if (values.photos) query.set("with_photos", "true");
    if (values.sort && values.sort !== "newest") query.set("sort", values.sort);
    router.push(`${basePath}${query.toString() ? `?${query}` : ""}`);
    setOpen(false);
  };

  const reset = () => {
    setValues({
      q: "",
      purposes: [],
      species: "",
      sex: "",
      minAge: "",
      maxAge: "",
      size: "",
      cityId: "",
      priceMin: "",
      priceMax: "",
      pedigree: "",
      vaccinated: "",
      photos: false,
      sort: "newest",
    });
    router.push(basePath);
    setOpen(false);
  };

  return (
    <>
      <button
        type="button"
        className="btn btn-secondary filters-toggle"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
      >
        <FilterIcon /> Фильтры
        {initial.purposes.length + (initial.species ? 1 : 0) + (initial.cityId ? 1 : 0) > 0 && (
          <span className="filter-count">
            {initial.purposes.length +
              (initial.species ? 1 : 0) +
              (initial.cityId ? 1 : 0) +
              (initial.pedigree ? 1 : 0)}
          </span>
        )}
      </button>
      <form className="filters" onSubmit={apply} data-open={open}>
        <div className="filters-head">
          <h2>Фильтры</h2>
          <button type="button" className="filters-reset" onClick={reset}>
            Сбросить
          </button>
        </div>

        <div className="field filter-search">
          <label htmlFor="filter-q">Что ищем</label>
          <div className="input-with-icon">
            <SearchIcon width={17} height={17} />
            <input
              id="filter-q"
              className="input"
              value={values.q}
              onChange={(event) => set("q", event.target.value)}
              placeholder="Порода, имя, город"
              autoComplete="off"
            />
          </div>
        </div>

        <fieldset className="filter-group">
          <legend>Цель</legend>
          {purposes.map((purpose) => (
            <label key={purpose.value} className="check check-compact">
              <input
                type="checkbox"
                checked={values.purposes.includes(purpose.value)}
                onChange={() => togglePurpose(purpose.value)}
              />
              {purpose.label}
            </label>
          ))}
        </fieldset>

        <div className="filter-row">
          <div className="field">
            <label htmlFor="filter-species">Вид</label>
            <select
              id="filter-species"
              className="select"
              value={values.species}
              onChange={(event) => set("species", event.target.value)}
            >
              <option value="">Любой</option>
              {species.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-sex">Пол</label>
            <select
              id="filter-sex"
              className="select"
              value={values.sex}
              onChange={(event) => set("sex", event.target.value)}
            >
              <option value="">Любой</option>
              <option value="male">Мальчик</option>
              <option value="female">Девочка</option>
            </select>
          </div>
        </div>

        <div className="filter-row">
          <div className="field">
            <label htmlFor="filter-age-min">Возраст от</label>
            <input
              id="filter-age-min"
              className="input"
              inputMode="numeric"
              value={values.minAge}
              onChange={(event) => set("minAge", event.target.value)}
              placeholder="0"
            />
          </div>
          <div className="field">
            <label htmlFor="filter-age-max">до</label>
            <input
              id="filter-age-max"
              className="input"
              inputMode="numeric"
              value={values.maxAge}
              onChange={(event) => set("maxAge", event.target.value)}
              placeholder="20"
            />
          </div>
        </div>

        <div className="field">
          <label htmlFor="filter-city">Город</label>
          <select
            id="filter-city"
            className="select"
            value={values.cityId}
            onChange={(event) => set("cityId", event.target.value)}
          >
            <option value="">Все города</option>
            {dictionaries?.cities.map((city) => (
              <option key={city.id} value={city.id}>
                {city.name}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label htmlFor="filter-size">Размер</label>
          <select
            id="filter-size"
            className="select"
            value={values.size}
            onChange={(event) => set("size", event.target.value)}
          >
            <option value="">Любой</option>
            <option value="small">Маленький</option>
            <option value="medium">Средний</option>
            <option value="large">Крупный</option>
          </select>
        </div>

        <div className="filter-row">
          <div className="field">
            <label htmlFor="price-min">Цена от, ₽</label>
            <input
              id="price-min"
              className="input"
              inputMode="numeric"
              value={values.priceMin}
              onChange={(event) => set("priceMin", event.target.value)}
              placeholder="0"
            />
          </div>
          <div className="field">
            <label htmlFor="price-max">до, ₽</label>
            <input
              id="price-max"
              className="input"
              inputMode="numeric"
              value={values.priceMax}
              onChange={(event) => set("priceMax", event.target.value)}
              placeholder="100 000"
            />
          </div>
        </div>

        <div className="filter-row">
          <div className="field">
            <label htmlFor="filter-pedigree">Родословная</label>
            <select
              id="filter-pedigree"
              className="select"
              value={values.pedigree}
              onChange={(event) => set("pedigree", event.target.value)}
            >
              <option value="">Неважно</option>
              <option value="true">Есть</option>
              <option value="false">Нет</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter-vaccinated">Прививки</label>
            <select
              id="filter-vaccinated"
              className="select"
              value={values.vaccinated}
              onChange={(event) => set("vaccinated", event.target.value)}
            >
              <option value="">Неважно</option>
              <option value="true">Есть</option>
              <option value="false">Нет</option>
            </select>
          </div>
        </div>

        <label className="check">
          <input
            type="checkbox"
            checked={values.photos}
            onChange={(event) => set("photos", event.target.checked)}
          />
          Только с фотографиями
        </label>

        <div className="field">
          <label htmlFor="filter-sort">Сортировка</label>
          <select
            id="filter-sort"
            className="select"
            value={values.sort}
            onChange={(event) => set("sort", event.target.value)}
          >
            <option value="newest">Сначала новые</option>
            <option value="price_asc">Цена: по возрастанию</option>
            <option value="price_desc">Цена: по убыванию</option>
          </select>
        </div>

        <button type="submit" className="btn btn-primary filters-submit">
          Показать результаты
        </button>
      </form>
    </>
  );
}
