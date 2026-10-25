"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import { useAuth } from "./auth-provider";
import { CheckIcon, DocumentIcon, ImageIcon, PawIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { ageFromBirthDate, formatAge, formatPrice, purposeLabel } from "@/lib/format";
import type { Dictionaries, OwnerAnimal, OwnerListing, Purpose, Species } from "@/lib/types";

const steps = [
  "Цель",
  "Животное",
  "Здоровье",
  "Фотографии",
  "Цена и город",
  "Описание",
  "Публикация",
];

const purposes: { value: Purpose; label: string; hint: string }[] = [
  { value: "sale", label: "Продажа", hint: "Передача животного за плату" },
  { value: "mating", label: "Вязка", hint: "Поиск пары для знакомства" },
  { value: "breeding_pedigree", label: "Племенное разведение", hint: "Пара с родословной" },
  { value: "adoption", label: "Отдам в добрые руки", hint: "Бесплатно, без цены" },
  { value: "rehoming", label: "Переустройство", hint: "Новый дом по семейным обстоятельствам" },
];

const speciesOptions = [
  { value: "dog", label: "Собака" },
  { value: "cat", label: "Кошка" },
  { value: "bird", label: "Птица" },
  { value: "rodent", label: "Грызун" },
  { value: "reptile", label: "Рептилия" },
  { value: "other", label: "Другое" },
];

const TODAY = new Date();
const TODAY_ISO = TODAY.toISOString().slice(0, 10);

export function ListingWizard({
  dictionaries,
  initialListing,
  initialAnimal,
  listingsPath = "/account/listings",
}: {
  dictionaries: Dictionaries | null;
  initialListing?: OwnerListing | null;
  initialAnimal?: OwnerAnimal | null;
  listingsPath?: string;
}) {
  const router = useRouter();
  const { user } = useAuth();
  const showToast = useToast();
  const editing = Boolean(initialListing && initialAnimal);
  const [step, setStep] = useState(editing ? 1 : 0);
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [animalId, setAnimalId] = useState<string | null>(initialAnimal?.public_id ?? null);
  const [listingId, setListingId] = useState<string | null>(initialListing?.public_id ?? null);
  const [photos, setPhotos] = useState<OwnerAnimal["photos"]>(initialAnimal?.photos ?? []);
  const [uploading, setUploading] = useState(false);
  const [dragPhoto, setDragPhoto] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [consents, setConsents] = useState({
    adult: false,
    welfare: false,
    photoRights: false,
    noProhibited: false,
    accuracy: false,
  });

  const [form, setForm] = useState({
    purpose: (initialListing?.purpose ?? "sale") as Purpose,
    name: initialAnimal?.name ?? "",
    species: initialAnimal?.species ?? "dog",
    breed: initialAnimal?.breed ?? "",
    sex: initialAnimal?.sex ?? "unknown",
    birthDate: initialAnimal?.birth_date ?? "",
    colour: initialAnimal?.colour ?? "",
    size: initialAnimal?.size ?? "unknown",
    vaccinated:
      initialAnimal?.vaccinated === null || initialAnimal?.vaccinated === undefined
        ? ""
        : initialAnimal.vaccinated
          ? "true"
          : "false",
    healthNotes: initialAnimal?.health_notes ?? "",
    animalDescription: initialAnimal?.description ?? "",
    hasPedigree: initialAnimal?.has_pedigree ?? false,
    pedigreeRegistry: initialAnimal?.pedigree_registry ?? "",
    pedigreeNumber: initialAnimal?.pedigree_number ?? "",
    title: initialListing?.title ?? "",
    description: initialListing?.description ?? "",
    priceRub: initialListing?.price_kopecks ? String(initialListing.price_kopecks / 100) : "",
    negotiable: initialListing?.negotiable ?? false,
    cityId:
      initialListing?.city_id !== null && initialListing?.city_id !== undefined
        ? String(initialListing.city_id)
        : user?.city_id
          ? String(user.city_id)
          : "",
  });

  const update = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  const selectedCity = dictionaries?.cities.find((city) => String(city.id) === form.cityId);
  const region = dictionaries?.regions.find((item) => item.id === selectedCity?.region_id);
  const defaultTitle = useMemo(() => {
    const animal = form.name.trim();
    if (!animal) return "";
    return `${form.breed.trim() ? `${form.breed.trim()}, ` : ""}${animal} — ${purposeLabel(form.purpose)}`;
  }, [form.breed, form.name, form.purpose]);

  const animalPayload = () => ({
    name: form.name.trim(),
    species: form.species,
    breed_text: form.breed.trim() || null,
    sex: form.sex,
    birth_date: form.birthDate || null,
    colour: form.colour.trim() || null,
    size: form.size,
    has_pedigree: form.hasPedigree,
    pedigree_registry: form.hasPedigree ? form.pedigreeRegistry.trim() || null : null,
    pedigree_number: form.hasPedigree ? form.pedigreeNumber.trim() || null : null,
    vaccinated: form.vaccinated === "" ? null : form.vaccinated === "true",
    health_notes: form.healthNotes.trim() || null,
    description: form.animalDescription.trim() || null,
  });

  const listingPayload = () => {
    const noPrice = form.purpose === "adoption" || form.purpose === "rehoming";
    const price = noPrice || !form.priceRub ? null : Math.round(Number(form.priceRub) * 100);
    return {
      title: (form.title.trim() || defaultTitle || `${form.name}, ${form.species}`).slice(0, 140),
      description: form.description.trim(),
      price_kopecks: price,
      negotiable: noPrice ? false : form.negotiable,
      city_id: form.cityId ? Number(form.cityId) : null,
      region_id: region?.id ?? null,
    };
  };

  const saveAnimal = async (): Promise<string> => {
    if (animalId) {
      await api<OwnerAnimal>(`/api/v1/animals/${animalId}`, {
        method: "PATCH",
        body: animalPayload(),
      });
      return animalId;
    }
    const created = await api<OwnerAnimal>("/api/v1/animals", {
      method: "POST",
      body: animalPayload(),
    });
    setAnimalId(created.public_id);
    return created.public_id;
  };

  const saveListing = async (id: string) => {
    if (listingId) {
      await api<OwnerListing>(`/api/v1/listings/${listingId}`, {
        method: "PATCH",
        body: listingPayload(),
      });
      return listingId;
    }
    const created = await api<OwnerListing>("/api/v1/listings", {
      method: "POST",
      body: { ...listingPayload(), animal_id: id, purpose: form.purpose },
    });
    setListingId(created.public_id);
    return created.public_id;
  };

  const validateStep = (current: number): string => {
    if (current === 1) {
      if (!form.name.trim()) return "Укажите имя животного.";
      if (form.hasPedigree && !form.pedigreeRegistry.trim()) {
        return "Для родословной укажите реестр (например, РКФ или WCF).";
      }
    }
    if (current === 3 && photos.length === 0) {
      return "Добавьте хотя бы одну фотографию — без неё объявление не опубликовать.";
    }
    if (current === 4) {
      if (form.purpose === "sale" && !form.priceRub && !form.negotiable) {
        return "Укажите цену или отметьте «По договорённости».";
      }
      if (form.purpose === "sale" && form.priceRub && Number(form.priceRub) <= 0) {
        return "Цена должна быть больше нуля.";
      }
    }
    return "";
  };

  const next = async () => {
    const message = validateStep(step);
    if (message) {
      setError(message);
      return;
    }
    setError("");
    setBusy(true);
    setSaving(true);
    try {
      if (step >= 1) {
        const id = await saveAnimal();
        await saveListing(id);
      }
      setStep((current) => Math.min(steps.length - 1, current + 1));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Не удалось сохранить черновик.");
    } finally {
      setBusy(false);
      setSaving(false);
    }
  };

  const back = () => {
    setError("");
    setStep((current) => Math.max(0, current - 1));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const uploadFiles = async (files: FileList | File[]) => {
    if (!animalId) {
      setError("Сначала сохраните данные животного.");
      return;
    }
    if (photos.length + files.length > 10) {
      setError("Можно загрузить не более 10 фотографий.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      for (const file of Array.from(files)) {
        if (!file.type.startsWith("image/")) continue;
        const data = new FormData();
        data.append("file", file);
        const photo = await api<OwnerAnimal["photos"][number]>(
          `/api/v1/animals/${animalId}/photos`,
          { method: "POST", formData: data },
        );
        setPhotos((current) => [...current, photo]);
      }
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Не удалось загрузить фотографию.");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const removePhoto = async (photoId: string) => {
    if (!animalId) return;
    try {
      await api(`/api/v1/animals/${animalId}/photos/${photoId}`, { method: "DELETE" });
      setPhotos((current) => current.filter((photo) => photo.id !== photoId));
    } catch {
      showToast("Не удалось удалить фотографию", "error");
    }
  };

  const makePrimary = async (photoId: string) => {
    if (!animalId) return;
    try {
      await api(`/api/v1/animals/${animalId}/photos/${photoId}/primary`, { method: "POST" });
      setPhotos((current) =>
        current.map((photo) => ({ ...photo, is_primary: photo.id === photoId })),
      );
      showToast("Главная фотография обновлена");
    } catch {
      showToast("Не удалось выбрать главную фотографию", "error");
    }
  };

  const reorder = async (targetId: string) => {
    if (!animalId || !dragPhoto || dragPhoto === targetId) return;
    const current = [...photos];
    const from = current.findIndex((photo) => photo.id === dragPhoto);
    const to = current.findIndex((photo) => photo.id === targetId);
    if (from < 0 || to < 0) return;
    const [moved] = current.splice(from, 1);
    current.splice(to, 0, moved);
    setPhotos(current.map((photo, index) => ({ ...photo, position: index })));
    try {
      await api(`/api/v1/animals/${animalId}/photos/order`, {
        method: "PUT",
        body: current.map((photo) => photo.id),
      });
    } catch {
      showToast("Не удалось сохранить порядок фотографий", "error");
    } finally {
      setDragPhoto(null);
    }
  };

  const publish = async () => {
    if (!listingId || !animalId) {
      setError("Черновик ещё не сохранён. Вернитесь на шаг с фотографиями.");
      return;
    }
    if (!Object.values(consents).every(Boolean)) {
      setError("Подтвердите все обязательные пункты перед публикацией.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await saveAnimal();
      await saveListing(animalId);
      const result = await api<OwnerListing>(`/api/v1/listings/${listingId}/publish`, {
        method: "POST",
        body: {
          confirm_adult: consents.adult,
          confirm_animal_welfare: consents.welfare,
          confirm_photo_rights: consents.photoRights,
          confirm_no_prohibited: consents.noProhibited,
          confirm_accuracy: consents.accuracy,
        },
      });
      if (result.status === "published") {
        showToast(editing ? "Изменения опубликованы" : "Объявление опубликовано", "success");
      } else {
        showToast("Объявление отправлено на проверку");
      }
      router.push(listingsPath);
      router.refresh();
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Не удалось опубликовать объявление.");
    } finally {
      setBusy(false);
    }
  };

  const toggleConsent = (key: keyof typeof consents) =>
    setConsents((current) => ({ ...current, [key]: !current[key] }));

  const savingLabel = saving
    ? "Сохраняем…"
    : listingId
      ? "Черновик сохранён"
      : "Черновик создастся автоматически";

  return (
    <div className="wizard">
      <aside className="wizard-steps" aria-label="Шаги создания объявления">
        {steps.map((title, index) => (
          <div
            className="wizard-step"
            key={title}
            data-state={index === step ? "current" : index < step ? "done" : "upcoming"}
          >
            <span className="wizard-step-num">
              {index < step ? <CheckIcon width={13} height={13} /> : index + 1}
            </span>
            {title}
          </div>
        ))}
        <span className="wizard-save-state">{savingLabel}</span>
      </aside>

      <section className="wizard-panel">
        {error && (
          <div className="form-error" role="alert">
            {error}
          </div>
        )}

        {step === 0 && (
          <>
            <h2>Что вы хотите сделать?</h2>
            <p>
              {editing
                ? "Цель объявления нельзя изменить после создания. Для другой цели создайте новое объявление."
                : "От этого зависят поля, цена и то, как объявление увидят другие."}
            </p>
            <div className="purpose-grid">
              {purposes.map((purpose) => (
                <button
                  type="button"
                  key={purpose.value}
                  className="purpose-card"
                  data-selected={form.purpose === purpose.value}
                  disabled={editing}
                  onClick={() => update("purpose", purpose.value)}
                >
                  <span className="purpose-check">
                    {form.purpose === purpose.value && <CheckIcon width={14} height={14} />}
                  </span>
                  <strong>{purpose.label}</strong>
                  <span>{purpose.hint}</span>
                </button>
              ))}
            </div>
          </>
        )}

        {step === 1 && (
          <>
            <h2>Расскажите о животном</h2>
            <p>Эти данные увидят все, кто откроет объявление.</p>
            <div className="field-row">
              <div className="field">
                <label htmlFor="wizard-name">Имя *</label>
                <input
                  id="wizard-name"
                  className="input"
                  value={form.name}
                  onChange={(event) => update("name", event.target.value)}
                  maxLength={80}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="wizard-species">Вид *</label>
                <select
                  id="wizard-species"
                  className="select"
                  value={form.species}
                  onChange={(event) => update("species", event.target.value as Species)}
                >
                  {speciesOptions.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="wizard-breed">Порода</label>
                <input
                  id="wizard-breed"
                  className="input"
                  list="breed-options"
                  value={form.breed}
                  onChange={(event) => update("breed", event.target.value)}
                  maxLength={120}
                />
                <datalist id="breed-options">
                  {dictionaries?.breeds
                    .filter((breed) => !breed.species || breed.species === form.species)
                    .map((breed) => (
                      <option key={breed.id} value={breed.name} />
                    ))}
                </datalist>
              </div>
              <div className="field">
                <label htmlFor="wizard-sex">Пол *</label>
                <select
                  id="wizard-sex"
                  className="select"
                  value={form.sex}
                  onChange={(event) => update("sex", event.target.value)}
                >
                  <option value="unknown">Не указывать</option>
                  <option value="male">Мальчик</option>
                  <option value="female">Девочка</option>
                </select>
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="wizard-birth">Дата рождения</label>
                <input
                  id="wizard-birth"
                  className="input"
                  type="date"
                  value={form.birthDate}
                  max={TODAY_ISO}
                  onChange={(event) => update("birthDate", event.target.value)}
                />
                {form.birthDate && (
                  <span className="field-hint">
                    Возраст: {formatAge(ageFromBirthDate(form.birthDate, TODAY))}
                  </span>
                )}
              </div>
              <div className="field">
                <label htmlFor="wizard-size">Размер</label>
                <select
                  id="wizard-size"
                  className="select"
                  value={form.size}
                  onChange={(event) => update("size", event.target.value)}
                >
                  <option value="unknown">Не указывать</option>
                  <option value="small">Маленький</option>
                  <option value="medium">Средний</option>
                  <option value="large">Крупный</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="wizard-colour">Окрас</label>
              <input
                id="wizard-colour"
                className="input"
                value={form.colour}
                onChange={(event) => update("colour", event.target.value)}
                maxLength={80}
                placeholder="Например, рыжий с белым"
              />
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h2>Здоровье и документы</h2>
            <p>
              Это заявления владельца, а не медицинское заключение. Будьте точны: доверие важнее
              идеальной анкеты.
            </p>
            <div className="field">
              <label htmlFor="wizard-vaccinated">Прививки</label>
              <select
                id="wizard-vaccinated"
                className="select"
                value={form.vaccinated}
                onChange={(event) => update("vaccinated", event.target.value)}
              >
                <option value="">Не указывать</option>
                <option value="true">Есть</option>
                <option value="false">Нет</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="wizard-health">Заметки о здоровье</label>
              <textarea
                id="wizard-health"
                className="textarea"
                value={form.healthNotes}
                onChange={(event) => update("healthNotes", event.target.value)}
                maxLength={2000}
                rows={4}
                placeholder="Особенности питания, аллергии, ветеринарные ограничения"
              />
            </div>
            <label className="check">
              <input
                type="checkbox"
                checked={form.hasPedigree}
                onChange={(event) => update("hasPedigree", event.target.checked)}
              />
              У животного есть родословная
            </label>
            {form.hasPedigree && (
              <div className="field-row">
                <div className="field">
                  <label htmlFor="wizard-registry">Реестр *</label>
                  <input
                    id="wizard-registry"
                    className="input"
                    value={form.pedigreeRegistry}
                    onChange={(event) => update("pedigreeRegistry", event.target.value)}
                    maxLength={40}
                    placeholder="РКФ, FCI, WCF"
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="wizard-pedigree-number">Номер документа</label>
                  <input
                    id="wizard-pedigree-number"
                    className="input"
                    value={form.pedigreeNumber}
                    onChange={(event) => update("pedigreeNumber", event.target.value)}
                    maxLength={80}
                  />
                </div>
              </div>
            )}
            <div className="notice">
              <DocumentIcon width={18} height={18} /> Документ можно загрузить позже в разделе «Мои
              животные». Он хранится приватно и доступен только вам и модерации.
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h2>Фотографии</h2>
            <p>
              От 1 до 10 фотографий. Первая станет главной. Перетаскивайте плитки, чтобы изменить
              порядок.
            </p>
            <div className="photo-grid">
              {photos.map((photo, index) => (
                <div
                  className="photo-tile"
                  key={photo.id}
                  draggable
                  onDragStart={() => setDragPhoto(photo.id)}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => void reorder(photo.id)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={photo.thumb_url} alt={photo.alt_text ?? `Фото ${index + 1}`} />
                  {photo.is_primary && <span className="primary-badge">Главная</span>}
                  <button
                    type="button"
                    onClick={() => void removePhoto(photo.id)}
                    aria-label="Удалить фотографию"
                  >
                    ×
                  </button>
                  {!photo.is_primary && (
                    <button
                      type="button"
                      className="photo-primary-button"
                      onClick={() => void makePrimary(photo.id)}
                    >
                      Сделать главной
                    </button>
                  )}
                </div>
              ))}
              {photos.length < 10 && (
                <button
                  type="button"
                  className="upload-tile"
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading || !animalId}
                >
                  <ImageIcon width={24} height={24} />
                  {uploading ? "Загружаем…" : "Добавить фото"}
                  <small>JPEG, PNG или WebP</small>
                </button>
              )}
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              hidden
              onChange={(event) => {
                if (event.target.files?.length) void uploadFiles(event.target.files);
              }}
            />
            {!animalId && (
              <p className="field-hint">
                Черновик животного создастся после возврата на предыдущий шаг.
              </p>
            )}
          </>
        )}

        {step === 4 && (
          <>
            <h2>Цена и город</h2>
            <p>Точный адрес не публикуется — только город и регион.</p>
            {form.purpose === "adoption" || form.purpose === "rehoming" ? (
              <div className="notice">
                Для пристройства цена не указывается. Объявление будет отмечено как бесплатное.
              </div>
            ) : (
              <>
                <div className="field">
                  <label htmlFor="wizard-price">Цена, ₽</label>
                  <input
                    id="wizard-price"
                    className="input"
                    inputMode="numeric"
                    value={form.priceRub}
                    onChange={(event) =>
                      update("priceRub", event.target.value.replace(/[^\d]/g, ""))
                    }
                    placeholder="Например, 45000"
                  />
                </div>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={form.negotiable}
                    onChange={(event) => update("negotiable", event.target.checked)}
                  />
                  Цена договорная
                </label>
              </>
            )}
            <div className="field">
              <label htmlFor="wizard-city">Город</label>
              <select
                id="wizard-city"
                className="select"
                value={form.cityId}
                onChange={(event) => update("cityId", event.target.value)}
              >
                <option value="">Не указывать</option>
                {dictionaries?.cities.map((city) => (
                  <option key={city.id} value={city.id}>
                    {city.name}
                  </option>
                ))}
              </select>
              {region && <span className="field-hint">Регион: {region.name}</span>}
            </div>
          </>
        )}

        {step === 5 && (
          <>
            <h2>История и описание</h2>
            <p>Расскажите о характере, привычках и условиях передачи.</p>
            <div className="field">
              <label htmlFor="wizard-title">Заголовок объявления</label>
              <input
                id="wizard-title"
                className="input"
                value={form.title || defaultTitle}
                onChange={(event) => update("title", event.target.value)}
                maxLength={140}
              />
              <span className="field-hint">{(form.title || defaultTitle).length} / 140</span>
            </div>
            <div className="field">
              <label htmlFor="wizard-animal-story">О животном</label>
              <textarea
                id="wizard-animal-story"
                className="textarea"
                value={form.animalDescription}
                onChange={(event) => update("animalDescription", event.target.value)}
                maxLength={4000}
                rows={5}
                placeholder="Характер, привычки, любимые занятия, как относится к людям и другим животным"
              />
              <span className="field-hint">{form.animalDescription.length} / 4000</span>
            </div>
            <div className="field">
              <label htmlFor="wizard-description">Условия и важные детали</label>
              <textarea
                id="wizard-description"
                className="textarea"
                value={form.description}
                onChange={(event) => update("description", event.target.value)}
                maxLength={5000}
                rows={5}
                placeholder="Что входит, как проходит передача, что важно обсудить"
              />
              <span className="field-hint">{form.description.length} / 5000</span>
            </div>
            <p className="field-hint">
              Не указывайте телефон, почту, Telegram или точный адрес — это нарушает правила и
              скрывается автоматически.
            </p>
          </>
        )}

        {step === 6 && (
          <>
            <h2>Проверьте перед публикацией</h2>
            <p>Так объявление увидят другие пользователи.</p>
            <div className="preview-card">
              {(photos.find((photo) => photo.is_primary) ?? photos[0]) ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={(photos.find((photo) => photo.is_primary) ?? photos[0]).url}
                  alt="Главная фотография объявления"
                />
              ) : (
                <div className="preview-placeholder">
                  <PawIcon width={44} height={44} />
                </div>
              )}
              <div>
                <div className="badge-row">
                  <span className="chip chip-brand">{purposeLabel(form.purpose)}</span>
                  {form.hasPedigree && <span className="chip chip-live">Родословная</span>}
                </div>
                <h3 className="preview-title">{form.title || defaultTitle}</h3>
                <p className="preview-price">
                  {formatPrice(
                    form.purpose === "adoption" || form.purpose === "rehoming"
                      ? null
                      : form.priceRub
                        ? Number(form.priceRub) * 100
                        : null,
                    form.negotiable,
                  )}
                </p>
                <p className="muted">
                  {[form.name, form.breed, selectedCity?.name].filter(Boolean).join(" · ")}
                </p>
                <p>{form.animalDescription || "Описание животного пока не заполнено."}</p>
              </div>
            </div>
            <div className="publish-checks">
              <label className="check">
                <input
                  type="checkbox"
                  checked={consents.adult}
                  onChange={() => toggleConsent("adult")}
                />{" "}
                Мне исполнилось 18 лет.
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={consents.noProhibited}
                  onChange={() => toggleConsent("noProhibited")}
                />{" "}
                Я подтверждаю, что животное не относится к запрещённым к обороту видам.
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={consents.photoRights}
                  onChange={() => toggleConsent("photoRights")}
                />{" "}
                Фотографии мои или у меня есть право их публиковать.
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={consents.accuracy}
                  onChange={() => toggleConsent("accuracy")}
                />{" "}
                Данные точны, а условия передачи не нарушают благополучие животного.
              </label>
              <label className="check">
                <input
                  type="checkbox"
                  checked={consents.welfare}
                  onChange={() => toggleConsent("welfare")}
                />{" "}
                Я не передаю животное на бои, для жестокого обращения или незаконной торговли.
              </label>
            </div>
            <div className="notice">
              Чистые объявления публикуются сразу. Если автоматическая проверка найдёт спорные
              детали, объявление попадёт к модератору.
            </div>
          </>
        )}

        <div className="wizard-actions">
          {step > 0 && (
            <button type="button" className="btn btn-ghost" onClick={back} disabled={busy}>
              Назад
            </button>
          )}
          {step < steps.length - 1 ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void next()}
              disabled={busy}
            >
              {busy ? "Сохраняем…" : "Продолжить"}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void publish()}
              disabled={busy}
            >
              {busy ? "Публикуем…" : editing ? "Опубликовать изменения" : "Опубликовать объявление"}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
