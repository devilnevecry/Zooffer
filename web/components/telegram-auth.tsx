"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "./auth-provider";
import { api, ClientApiError } from "@/lib/client";
import { safeNext } from "@/lib/navigation";
import type { AuthResponse, TelegramLoginPayload } from "@/lib/types";

const botUsername = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "";
const botUrl =
  process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ??
  (botUsername ? `https://t.me/${botUsername}` : "");
const miniAppUrl = process.env.NEXT_PUBLIC_TELEGRAM_MINI_APP_URL ?? "";

declare global {
  interface Window {
    onZoofferTelegramAuth?: (user: TelegramLoginPayload) => void;
  }
}

/**
 * Telegram-only sign-in.
 *
 * Email/password registration, phone verification and password recovery are not
 * part of the product: one Telegram identity covers the website, the bot and the
 * Mini App. The Login Widget is used when a bot username is configured; otherwise
 * the user is sent to the bot, which creates the same account after consent.
 */
export function TelegramAuth({ intent = "login" }: { intent?: "login" | "register" }) {
  const router = useRouter();
  const params = useSearchParams();
  const { setSession } = useAuth();
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get("next"));

  const complete = useCallback(
    async (payload: TelegramLoginPayload) => {
      setBusy(true);
      setError("");
      try {
        const session = await api<AuthResponse>("/api/v1/auth/telegram", {
          method: "POST",
          body: payload,
        });
        setSession(session);
        router.replace(next);
        router.refresh();
      } catch (err) {
        setError(
          err instanceof ClientApiError
            ? err.message
            : "Не удалось войти через Telegram. Попробуйте ещё раз.",
        );
        setBusy(false);
      }
    },
    [next, router, setSession],
  );

  useEffect(() => {
    const host = containerRef.current;
    if (!botUsername || !host) return;
    window.onZoofferTelegramAuth = (user: TelegramLoginPayload) => {
      void complete(user);
    };
    const script = document.createElement("script");
    script.src = "https://telegram.org/js/telegram-widget.js?22";
    script.async = true;
    script.setAttribute("data-telegram-login", botUsername);
    script.setAttribute("data-size", "large");
    script.setAttribute("data-radius", "12");
    script.setAttribute("data-userpic", "false");
    script.setAttribute("data-request-access", "write");
    script.setAttribute("data-onauth", "onZoofferTelegramAuth(user)");
    host.appendChild(script);
    return () => {
      script.remove();
      delete window.onZoofferTelegramAuth;
    };
  }, [complete]);

  return (
    <div className="telegram-auth">
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}

      {botUsername ? (
        <div className="telegram-widget" ref={containerRef} aria-busy={busy} />
      ) : (
        <p className="muted small">
          Кнопка входа через Telegram появится после настройки бота. Пока откройте бота и
          отправьте /start.
        </p>
      )}

      {botUrl && (
        <a className="btn btn-secondary auth-submit" href={botUrl} target="_blank" rel="noreferrer">
          {intent === "register" ? "Создать аккаунт в Telegram" : "Открыть бота Zooffer"}
        </a>
      )}

      {miniAppUrl && (
        <a className="text-link" href={miniAppUrl} target="_blank" rel="noreferrer">
          Открыть Mini App
        </a>
      )}

      <p className="muted small">
        Продолжая, вы принимаете{" "}
        <Link href="/legal/terms" className="text-link">
          условия
        </Link>{" "}
        и{" "}
        <Link href="/legal/privacy" className="text-link">
          политику конфиденциальности
        </Link>
        . Почта и телефон не запрашиваются.
      </p>
    </div>
  );
}
