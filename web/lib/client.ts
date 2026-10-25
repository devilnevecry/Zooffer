let csrfToken: string | null = null;

export class ClientApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "request_failed") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function getCsrfToken() {
  return csrfToken;
}

async function ensureCsrf(): Promise<string | null> {
  if (csrfToken) return csrfToken;
  try {
    const response = await fetch("/api/v1/auth/me", { credentials: "same-origin" });
    if (!response.ok) return null;
    const body = (await response.json()) as { csrf_token?: string };
    if (body.csrf_token) {
      csrfToken = body.csrf_token;
      return csrfToken;
    }
  } catch {
    return null;
  }
  return null;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  signal?: AbortSignal;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? (options.body || options.formData ? "POST" : "GET");
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = await ensureCsrf();
    if (token) headers["X-CSRF-Token"] = token;
  }
  let response: Response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body:
        options.formData ?? (options.body !== undefined ? JSON.stringify(options.body) : undefined),
      credentials: "same-origin",
      signal: options.signal,
    });
  } catch {
    throw new ClientApiError("Нет соединения с сервером. Проверьте интернет.", 0, "network_error");
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = null;
    }
  }
  if (!response.ok) {
    const envelope = payload as { error?: { message?: string; code?: string } } | null;
    throw new ClientApiError(
      envelope?.error?.message ?? "Не удалось выполнить действие. Попробуйте ещё раз.",
      response.status,
      envelope?.error?.code,
    );
  }
  return payload as T;
}
