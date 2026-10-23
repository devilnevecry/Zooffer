import { cookies } from "next/headers";

import type { MeResponse } from "./types";

export const API_INTERNAL = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "request_failed") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

interface ServerFetchOptions {
  allow404?: boolean;
  allow401?: boolean;
}

export async function serverFetch<T>(
  path: string,
  options: ServerFetchOptions = {},
): Promise<T | null> {
  const jar = await cookies();
  const cookie = jar.toString();
  try {
    const response = await fetch(`${API_INTERNAL}${path}`, {
      headers: cookie ? { cookie } : undefined,
      cache: "no-store",
    });
    if (response.status === 404 && options.allow404) return null;
    if (response.status === 401 && options.allow401) return null;
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getMe(): Promise<MeResponse | null> {
  return serverFetch<MeResponse>("/api/v1/auth/me", { allow401: true });
}
