"use client";

export function paramValue(
  params: Record<string, string | string[] | undefined>,
  key: string,
): string {
  const value = params[key];
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export function numberParam(
  params: Record<string, string | string[] | undefined>,
  key: string,
): number | undefined {
  const value = paramValue(params, key);
  if (!value) return undefined;
  const number = Number(value);
  return Number.isFinite(number) ? number : undefined;
}
