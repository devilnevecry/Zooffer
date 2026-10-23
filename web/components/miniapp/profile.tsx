"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "../auth-provider";
import { ArrowIcon, ShieldIcon } from "../icons";
import { SettingsPanel } from "../settings-panel";
import { initials } from "@/lib/format";
import type {
  BlockedUserList,
  Dictionaries,
  NotificationPreferenceList,
  SessionList,
} from "@/lib/types";

import { useTelegram } from "./telegram";
import { MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

const quickLinks = [
  {
    href: "/tg/subscription",
    title: "Подписка",
    text: "План, лимиты и продление",
  },
  {
    href: "/tg/partners",
    title: "Партнёрам",
    text: "Предложения и сотрудничество",
  },
  {
    href: "/tg/support",
    title: "Поддержка",
    text: "Вопрос по аккаунту или объявлению",
  },
];

export function MiniProfile() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { webApp } = useTelegram();
  const [loggingOut, setLoggingOut] = useState(false);

  const dictionaries = useMiniApi<Dictionaries>("/api/v1/public/dictionaries");
  const sessions = useMiniApi<SessionList>("/api/v1/auth/sessions");
  const preferences = useMiniApi<NotificationPreferenceList>(
    "/api/v1/notification-preferences",
  );
  const blocked = useMiniApi<BlockedUserList>("/api/v1/blocked-users");

  if (!user) return <MiniLoading label="Открываем профиль…" />;

  const loading = !dictionaries.data || !sessions.data || !preferences.data || !blocked.data;
  const error = dictionaries.error || sessions.error || preferences.error || blocked.error;

  if (loading && !error) return <MiniLoading label="Загружаем настройки…" />;
  if (error) {
    return (
      <MiniError
        message={error}
        onRetry={() => {
          void dictionaries.reload();
          void sessions.reload();
          void preferences.reload();
          void blocked.reload();
        }}
      />
    );
  }

  const signOut = async () => {
    setLoggingOut(true);
    try {
      await logout();
      if (webApp) webApp.close();
      else router.push("/");
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <div className="tg-stack">
      <MiniPageHead eyebrow="Профиль" title={user.first_name ?? "Аккаунт"} />

      <section className="tg-profile-hero">
        <span className="avatar avatar-lg">{initials(user.first_name)}</span>
        <div className="grow">
          <strong>
            {[user.first_name, user.last_name].filter(Boolean).join(" ") || "Zooffer"}
          </strong>
          <span>{user.email ?? "Вход через Telegram"}</span>
        </div>
        <span className="chip chip-live">Аккаунт</span>
      </section>

      <div className="tg-quick-grid">
        {quickLinks.map((item) => (
          <Link href={item.href} className="tg-quick" key={item.href}>
            <span>
              <strong>{item.title}</strong>
              <small>{item.text}</small>
            </span>
            <ArrowIcon width={16} height={16} />
          </Link>
        ))}
      </div>

      <div className="tg-privacy">
        <ShieldIcon width={17} height={17} />
        <span>
          Другие видят только имя, фамилию (если указана) и город. Контакты, Telegram и
          история действий остаются приватными.
        </span>
      </div>

      <SettingsPanel
        user={user}
        dictionaries={dictionaries.data}
        sessions={sessions.data?.items ?? []}
        preferences={preferences.data ?? { items: [] }}
        blocked={blocked.data?.items ?? []}
        loginPath="/login"
        afterDeletePath="/"
        supportPath="/tg/support"
      />

      <button
        type="button"
        className="tg-logout"
        onClick={() => void signOut()}
        disabled={loggingOut}
      >
        {loggingOut ? "Выходим…" : "Выйти из аккаунта"}
      </button>
    </div>
  );
}
