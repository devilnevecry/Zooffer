import type { Purpose } from "./types";

export const PURPOSE_LABELS: Record<Purpose, string> = {
  sale: "Продажа",
  mating: "Вязка",
  breeding_pedigree: "Племенное разведение",
  adoption: "Отдам в добрые руки",
  rehoming: "Переустройство",
};

export const SPECIES_LABELS: Record<string, string> = {
  dog: "Собака",
  cat: "Кошка",
  bird: "Птица",
  rodent: "Грызун",
  reptile: "Рептилия",
  other: "Другое",
};

export const SEX_LABELS: Record<string, string> = {
  male: "Мальчик",
  female: "Девочка",
  unknown: "Не указан",
};

export const SIZE_LABELS: Record<string, string> = {
  small: "Маленький",
  medium: "Средний",
  large: "Крупный",
  unknown: "Не указан",
};

export const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending_moderation: "На проверке",
  published: "Опубликовано",
  paused: "Приостановлено",
  expired: "Истекло",
  sold: "Продан",
  archived: "В архиве",
  rejected: "Отклонено",
};

const nbsp = "\u202f";

export function formatPrice(kopecks: number | null, negotiable = false): string {
  if (kopecks === null) return negotiable ? "По договорённости" : "Цена не указана";
  const rubles = Math.round(kopecks / 100);
  return `${new Intl.NumberFormat("ru-RU").format(rubles).replace(/\s/g, nbsp)}${nbsp}₽`;
}

/**
 * Price label that respects the listing purpose. Adoption and rehoming
 * listings are not goods: an empty price there means "free to a good home",
 * not a missing value.
 */
export function formatListingPrice(
  purpose: string,
  kopecks: number | null,
  negotiable = false,
): string {
  if (kopecks !== null) return formatPrice(kopecks, negotiable);
  if (purpose === "adoption") return "В добрые руки";
  if (purpose === "rehoming") return "Переустройство";
  return formatPrice(null, negotiable);
}

export function formatAge(age: number | null): string {
  if (age === null) return "Возраст не указан";
  const mod10 = age % 10;
  const mod100 = age % 100;
  if (mod10 === 1 && mod100 !== 11) return `${age} год`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${age} года`;
  return `${age} лет`;
}

export function ageFromBirthDate(
  birthDate: string | null | undefined,
  today: Date,
): number | null {
  if (!birthDate) return null;
  const born = new Date(`${birthDate}T00:00:00Z`);
  if (Number.isNaN(born.getTime())) return null;
  let age = today.getUTCFullYear() - born.getUTCFullYear();
  const monthDelta = today.getUTCMonth() - born.getUTCMonth();
  if (monthDelta < 0 || (monthDelta === 0 && today.getUTCDate() < born.getUTCDate())) {
    age -= 1;
  }
  return Math.max(0, age);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function purposeLabel(purpose: string): string {
  return PURPOSE_LABELS[purpose as Purpose] ?? purpose;
}

export function speciesLabel(species: string): string {
  return SPECIES_LABELS[species] ?? species;
}

export function sexLabel(sex: string): string {
  return SEX_LABELS[sex] ?? sex;
}

export function sizeLabel(size: string): string {
  return SIZE_LABELS[size] ?? size;
}

export function initials(name: string | null | undefined): string {
  if (!name) return "Z";
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
