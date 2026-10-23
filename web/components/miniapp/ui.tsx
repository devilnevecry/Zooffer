"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { PawIcon } from "../icons";
import { api, ClientApiError } from "@/lib/client";

export function useMiniApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(Boolean(path));
  const [error, setError] = useState("");
  const request = useRef(0);

  const reload = useCallback(async () => {
    if (!path) return;
    const id = request.current + 1;
    request.current = id;
    setLoading(true);
    setError("");
    try {
      const payload = await api<T>(path);
      if (request.current === id) setData(payload);
    } catch (err) {
      if (request.current === id) {
        setError(
          err instanceof ClientApiError ? err.message : "Не удалось загрузить данные.",
        );
      }
    } finally {
      if (request.current === id) setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (!path) return;
    const id = request.current + 1;
    request.current = id;
    api<T>(path)
      .then((payload) => {
        if (request.current === id) {
          setData(payload);
          setError("");
        }
      })
      .catch((err) => {
        if (request.current === id) {
          setError(
            err instanceof ClientApiError ? err.message : "Не удалось загрузить данные.",
          );
        }
      })
      .finally(() => {
        if (request.current === id) setLoading(false);
      });
    return () => {
      request.current += 1;
    };
  }, [path]);

  return {
    data,
    setData,
    loading: loading || (Boolean(path) && data === null && !error),
    error,
    reload,
  };
}

export function MiniPageHead({
  eyebrow,
  title,
  lead,
  action,
}: {
  eyebrow: string;
  title: string;
  lead?: string;
  action?: ReactNode;
}) {
  return (
    <header className="tg-page-head">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        {lead && <p className="tg-lead">{lead}</p>}
      </div>
      {action}
    </header>
  );
}

export function MiniLoading({ label = "Загружаем…" }: { label?: string }) {
  return (
    <div className="tg-loading" role="status" aria-live="polite">
      <span className="tg-loader" />
      <span>{label}</span>
    </div>
  );
}

export function MiniError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="tg-empty" role="alert">
      <div className="tg-empty-icon">!</div>
      <h2>Не получилось загрузить</h2>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="btn btn-primary btn-sm" onClick={onRetry}>
          Попробовать снова
        </button>
      )}
    </div>
  );
}

export function MiniEmpty({
  title,
  text,
  href,
  action,
}: {
  title: string;
  text?: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="tg-empty">
      <div className="tg-empty-icon">
        <PawIcon width={28} height={28} />
      </div>
      <h2>{title}</h2>
      {text && <p>{text}</p>}
      {href && action && (
        <Link href={href} className="btn btn-primary btn-sm">
          {action}
        </Link>
      )}
    </div>
  );
}

export function MiniSection({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="tg-section">
      <div className="tg-section-head">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

export function MiniRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="tg-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
