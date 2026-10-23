"use client";

import Link from "next/link";
import { useState } from "react";

import { CheckIcon, DocumentIcon, EditIcon, ImageIcon, PawIcon, PlusIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDate, sexLabel, sizeLabel, speciesLabel } from "@/lib/format";
import type { DocumentList, Dictionaries, OwnerAnimal } from "@/lib/types";

type FormState = {
  name: string;
  breed: string;
  sex: string;
  birthDate: string;
  colour: string;
  size: string;
  vaccinated: string;
  healthNotes: string;
  description: string;
  hasPedigree: boolean;
  pedigreeRegistry: string;
  pedigreeNumber: string;
};

function formFor(animal: OwnerAnimal): FormState {
  return {
    name: animal.name,
    breed: animal.breed ?? "",
    sex: animal.sex,
    birthDate: animal.birth_date ?? "",
    colour: animal.colour ?? "",
    size: animal.size,
    vaccinated: animal.vaccinated === null ? "" : animal.vaccinated ? "true" : "false",
    healthNotes: animal.health_notes ?? "",
    description: animal.description ?? "",
    hasPedigree: animal.has_pedigree,
    pedigreeRegistry: animal.pedigree_registry ?? "",
    pedigreeNumber: animal.pedigree_number ?? "",
  };
}

export function AnimalManager({
  initial,
  dictionaries,
}: {
  initial: OwnerAnimal[];
  dictionaries: Dictionaries | null;
}) {
  const showToast = useToast();
  const [animals, setAnimals] = useState(initial);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploadingFor, setUploadingFor] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Record<string, DocumentList["items"]>>({});

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((current) => (current ? { ...current, [key]: value } : current));

  const startEdit = (animal: OwnerAnimal) => {
    setEditingId(animal.public_id);
    setForm(formFor(animal));
  };

  const save = async (animal: OwnerAnimal) => {
    if (!form) return;
    if (!form.name.trim()) {
      showToast("Укажите имя животного", "error");
      return;
    }
    if (form.hasPedigree && !form.pedigreeRegistry.trim()) {
      showToast("Укажите реестр родословной", "error");
      return;
    }
    setBusy(true);
    try {
      const updated = await api<OwnerAnimal>(`/api/v1/animals/${animal.public_id}`, {
        method: "PATCH",
        body: {
          name: form.name.trim(),
          breed_text: form.breed.trim() || null,
          sex: form.sex,
          birth_date: form.birthDate || null,
          colour: form.colour.trim() || null,
          size: form.size,
          vaccinated: form.vaccinated === "" ? null : form.vaccinated === "true",
          health_notes: form.healthNotes.trim() || null,
          description: form.description.trim() || null,
          has_pedigree: form.hasPedigree,
          pedigree_registry: form.hasPedigree ? form.pedigreeRegistry.trim() : null,
          pedigree_number: form.hasPedigree ? form.pedigreeNumber.trim() || null : null,
        },
      });
      setAnimals((items) =>
        items.map((item) => (item.public_id === updated.public_id ? updated : item)),
      );
      setEditingId(null);
      setForm(null);
      showToast("Данные животного обновлены", "success");
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось сохранить", "error");
    } finally {
      setBusy(false);
    }
  };

  const archive = async (animal: OwnerAnimal) => {
    if (!window.confirm(`Снять анкету «${animal.name}» с публикации? Она останется в архиве.`)) {
      return;
    }
    setBusy(true);
    try {
      await api(`/api/v1/animals/${animal.public_id}`, { method: "DELETE" });
      setAnimals((items) =>
        items.map((item) =>
          item.public_id === animal.public_id
            ? { ...item, archived_at: new Date().toISOString() }
            : item,
        ),
      );
      showToast("Анкета перенесена в архив");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось архивировать анкету",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  const uploadPhoto = async (animal: OwnerAnimal, file: File | undefined) => {
    if (!file) return;
    setUploadingFor(animal.public_id);
    try {
      const photo = await api<OwnerAnimal["photos"][number]>(
        `/api/v1/animals/${animal.public_id}/photos`,
        { method: "POST", formData: (() => { const data = new FormData(); data.append("file", file); return data; })() },
      );
      setAnimals((items) =>
        items.map((item) =>
          item.public_id === animal.public_id
            ? {
                ...item,
                photos: [...item.photos, photo].map((photoItem, index) => ({
                  ...photoItem,
                  position: index,
                })),
              }
            : item,
        ),
      );
      showToast("Фотография загружена", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось загрузить фотографию",
        "error",
      );
    } finally {
      setUploadingFor(null);
    }
  };

  const removePhoto = async (animal: OwnerAnimal, photoId: string) => {
    try {
      await api(`/api/v1/animals/${animal.public_id}/photos/${photoId}`, { method: "DELETE" });
      setAnimals((items) =>
        items.map((item) =>
          item.public_id === animal.public_id
            ? { ...item, photos: item.photos.filter((photo) => photo.id !== photoId) }
            : item,
        ),
      );
      showToast("Фотография удалена");
    } catch {
      showToast("Не удалось удалить фотографию", "error");
    }
  };

  const makePrimary = async (animal: OwnerAnimal, photoId: string) => {
    try {
      await api(`/api/v1/animals/${animal.public_id}/photos/${photoId}/primary`, {
        method: "POST",
      });
      setAnimals((items) =>
        items.map((item) =>
          item.public_id === animal.public_id
            ? {
                ...item,
                photos: item.photos.map((photo) => ({
                  ...photo,
                  is_primary: photo.id === photoId,
                })),
              }
            : item,
        ),
      );
      showToast("Главная фотография обновлена");
    } catch {
      showToast("Не удалось выбрать фотографию", "error");
    }
  };

  const loadDocuments = async (animal: OwnerAnimal) => {
    try {
      const result = await api<DocumentList>(
        `/api/v1/animals/${animal.public_id}/documents`,
      );
      setDocuments((current) => ({ ...current, [animal.public_id]: result.items }));
    } catch {
      showToast("Не удалось загрузить документы", "error");
    }
  };

  const uploadDocument = async (animal: OwnerAnimal, file: File | undefined) => {
    if (!file) return;
    try {
      const data = new FormData();
      data.append("file", file);
      const document = await api<DocumentList["items"][number]>(
        `/api/v1/animals/${animal.public_id}/documents`,
        { method: "POST", formData: data },
      );
      setDocuments((current) => ({
        ...current,
        [animal.public_id]: [document, ...(current[animal.public_id] ?? [])],
      }));
      showToast("Документ загружен и доступен только вам и модерации", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось загрузить документ",
        "error",
      );
    }
  };

  return (
    <div className="animal-manager">
      {animals.length === 0 && (
        <div className="empty-state">
          <PawIcon width={42} height={42} />
          <h2>Пока нет анкет животных</h2>
          <p>Создайте анкету и объявление — фотографии, здоровье и документы будут в одном месте.</p>
          <Link href="/account/listings/new" className="btn btn-primary">
            <PlusIcon /> Создать объявление
          </Link>
        </div>
      )}

      {animals.map((animal) => {
        const editing = editingId === animal.public_id;
        return (
          <article className="animal-card" key={animal.public_id}>
            <div className="animal-card-head">
              <div className="animal-avatar">
                {animal.photos[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={animal.photos[0].thumb_url} alt={animal.name} />
                ) : (
                  <PawIcon width={28} height={28} />
                )}
              </div>
              <div className="grow">
                <div className="badge-row">
                  <span className="chip chip-brand">{speciesLabel(animal.species)}</span>
                  <span className="chip">{sexLabel(animal.sex)}</span>
                  {animal.archived_at && <span className="chip chip-danger">В архиве</span>}
                  {animal.has_pedigree && <span className="chip chip-live">Родословная</span>}
                </div>
                <h2>
                  {animal.name}
                  {animal.breed ? `, ${animal.breed}` : ""}
                </h2>
                <p className="muted">
                  {animal.birth_date ? `Родился ${formatDate(animal.birth_date)}` : "Дата рождения не указана"}
                  {animal.colour ? ` · ${animal.colour}` : ""}
                  {animal.size !== "unknown" ? ` · ${sizeLabel(animal.size)}` : ""}
                </p>
              </div>
              <div className="manage-actions">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => (editing ? setEditingId(null) : startEdit(animal))}
                >
                  <EditIcon width={15} height={15} />
                  {editing ? "Закрыть" : "Изменить"}
                </button>
                {!animal.archived_at && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void archive(animal)}
                    disabled={busy}
                  >
                    В архив
                  </button>
                )}
              </div>
            </div>

            {editing && form && (
              <div className="animal-editor">
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`animal-name-${animal.public_id}`}>Имя *</label>
                    <input
                      id={`animal-name-${animal.public_id}`}
                      className="input"
                      value={form.name}
                      onChange={(event) => update("name", event.target.value)}
                      maxLength={80}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`animal-breed-${animal.public_id}`}>Порода</label>
                    <input
                      id={`animal-breed-${animal.public_id}`}
                      className="input"
                      list={`breeds-${animal.public_id}`}
                      value={form.breed}
                      onChange={(event) => update("breed", event.target.value)}
                      maxLength={120}
                    />
                    <datalist id={`breeds-${animal.public_id}`}>
                      {dictionaries?.breeds
                        .filter((breed) => !breed.species || breed.species === animal.species)
                        .map((breed) => (
                          <option key={breed.id} value={breed.name} />
                        ))}
                    </datalist>
                  </div>
                </div>
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`animal-sex-${animal.public_id}`}>Пол</label>
                    <select
                      id={`animal-sex-${animal.public_id}`}
                      className="select"
                      value={form.sex}
                      onChange={(event) => update("sex", event.target.value)}
                    >
                      <option value="unknown">Не указывать</option>
                      <option value="male">Мальчик</option>
                      <option value="female">Девочка</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor={`animal-birth-${animal.public_id}`}>Дата рождения</label>
                    <input
                      id={`animal-birth-${animal.public_id}`}
                      className="input"
                      type="date"
                      value={form.birthDate}
                      max={new Date().toISOString().slice(0, 10)}
                      onChange={(event) => update("birthDate", event.target.value)}
                    />
                  </div>
                </div>
                <div className="field-row">
                  <div className="field">
                    <label htmlFor={`animal-size-${animal.public_id}`}>Размер</label>
                    <select
                      id={`animal-size-${animal.public_id}`}
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
                  <div className="field">
                    <label htmlFor={`animal-colour-${animal.public_id}`}>Окрас</label>
                    <input
                      id={`animal-colour-${animal.public_id}`}
                      className="input"
                      value={form.colour}
                      onChange={(event) => update("colour", event.target.value)}
                      maxLength={80}
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor={`animal-vaccinated-${animal.public_id}`}>Прививки</label>
                  <select
                    id={`animal-vaccinated-${animal.public_id}`}
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
                  <label htmlFor={`animal-health-${animal.public_id}`}>Заметки о здоровье</label>
                  <textarea
                    id={`animal-health-${animal.public_id}`}
                    className="textarea"
                    rows={3}
                    value={form.healthNotes}
                    onChange={(event) => update("healthNotes", event.target.value)}
                    maxLength={2000}
                  />
                </div>
                <div className="field">
                  <label htmlFor={`animal-description-${animal.public_id}`}>О животном</label>
                  <textarea
                    id={`animal-description-${animal.public_id}`}
                    className="textarea"
                    rows={4}
                    value={form.description}
                    onChange={(event) => update("description", event.target.value)}
                    maxLength={4000}
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
                      <label htmlFor={`animal-registry-${animal.public_id}`}>Реестр *</label>
                      <input
                        id={`animal-registry-${animal.public_id}`}
                        className="input"
                        value={form.pedigreeRegistry}
                        onChange={(event) => update("pedigreeRegistry", event.target.value)}
                        maxLength={40}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`animal-pedigree-${animal.public_id}`}>Номер документа</label>
                      <input
                        id={`animal-pedigree-${animal.public_id}`}
                        className="input"
                        value={form.pedigreeNumber}
                        onChange={(event) => update("pedigreeNumber", event.target.value)}
                        maxLength={80}
                      />
                    </div>
                  </div>
                )}
                <div className="btn-row">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => void save(animal)}
                    disabled={busy}
                  >
                    <CheckIcon width={15} height={15} /> Сохранить
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => {
                      setEditingId(null);
                      setForm(null);
                    }}
                  >
                    Отмена
                  </button>
                </div>
              </div>
            )}

            <div className="animal-photos">
              {animal.photos.map((photo) => (
                <div className="animal-photo" key={photo.id}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={photo.thumb_url} alt={photo.alt_text ?? animal.name} />
                  {photo.is_primary && <span className="primary-badge">Главная</span>}
                  <div className="animal-photo-actions">
                    {!photo.is_primary && (
                      <button type="button" onClick={() => void makePrimary(animal, photo.id)}>
                        Главная
                      </button>
                    )}
                    <button type="button" onClick={() => void removePhoto(animal, photo.id)}>
                      Удалить
                    </button>
                  </div>
                </div>
              ))}
              {animal.photos.length < 10 && (
                <label className="upload-tile animal-upload">
                  <ImageIcon width={22} height={22} />
                  {uploadingFor === animal.public_id ? "Загружаем…" : "Добавить фото"}
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    hidden
                    onChange={(event) => {
                      void uploadPhoto(animal, event.target.files?.[0]);
                      event.target.value = "";
                    }}
                    disabled={uploadingFor === animal.public_id}
                  />
                </label>
              )}
            </div>

            <div className="animal-documents">
              <div className="animal-documents-head">
                <strong>
                  <DocumentIcon width={16} height={16} /> Документы
                </strong>
                <div className="btn-row">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void loadDocuments(animal)}
                  >
                    Показать
                  </button>
                  <label className="btn btn-secondary btn-sm">
                    Загрузить
                    <input
                      type="file"
                      accept="application/pdf,image/jpeg,image/png"
                      hidden
                      onChange={(event) => {
                        void uploadDocument(animal, event.target.files?.[0]);
                        event.target.value = "";
                      }}
                    />
                  </label>
                </div>
              </div>
              <p className="field-hint">
                Документы хранятся приватно. Их не видно в публичном объявлении.
              </p>
              {documents[animal.public_id]?.length ? (
                <ul className="document-list">
                  {documents[animal.public_id].map((document) => (
                    <li key={document.id}>
                      <DocumentIcon width={15} height={15} />
                      {document.document_type === "pedigree" ? "Родословная" : document.document_type}
                      <span className="muted"> · {formatDate(document.created_at)}</span>
                    </li>
                  ))}
                </ul>
              ) : documents[animal.public_id] ? (
                <p className="field-hint">Документов пока нет.</p>
              ) : null}
            </div>
          </article>
        );
      })}
    </div>
  );
}
