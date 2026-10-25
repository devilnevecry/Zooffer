"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { BellIcon, CheckIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api } from "@/lib/client";
import { formatDateTime } from "@/lib/format";
import type { NotificationItem, NotificationList } from "@/lib/types";

const categoryLabels: Record<string, string> = {
  matches: "Совпадения",
  messages: "Сообщения",
  inquiries: "Запросы",
  listing_moderation: "Объявления",
  subscriptions: "Подписка",
  partners: "Партнёры",
  support: "Поддержка",
  security: "Безопасность",
};

function linkFor(item: NotificationItem): string | null {
  const conversation = item.data?.conversation_public_id;
  if (conversation) return `/account/chats/${conversation}`;
  const listing = item.data?.listing_public_id;
  if (listing) return `/account/listings/${listing}`;
  const slug = item.data?.listing_slug;
  if (slug) return `/listing/${slug}`;
  return null;
}

export function NotificationCenter({ initial }: { initial: NotificationList }) {
  const router = useRouter();
  const showToast = useToast();
  const [items, setItems] = useState(initial.items);
  const [unread, setUnread] = useState(initial.unread_count);
  const [busy, setBusy] = useState(false);

  const markAll = async () => {
    setBusy(true);
    try {
      await api("/api/v1/notifications/read-all", { method: "POST" });
      const now = new Date().toISOString();
      setItems((current) => current.map((item) => ({ ...item, read_at: item.read_at ?? now })));
      setUnread(0);
      showToast("Все уведомления прочитаны");
      router.refresh();
    } catch {
      showToast("Не удалось отметить уведомления", "error");
    } finally {
      setBusy(false);
    }
  };

  const openItem = async (item: NotificationItem) => {
    if (!item.read_at) {
      try {
        await api(`/api/v1/notifications/${item.id}/read`, { method: "POST" });
        setItems((current) =>
          current.map((entry) =>
            entry.id === item.id ? { ...entry, read_at: new Date().toISOString() } : entry,
          ),
        );
        setUnread((value) => Math.max(0, value - 1));
      } catch {
        // Reading the notification is not a prerequisite for following its link.
      }
    }
    const link = linkFor(item);
    if (link) router.push(link);
  };

  if (!items.length) {
    return (
      <div className="empty-state">
        <BellIcon width={44} height={44} />
        <h2>Уведомлений пока нет</h2>
        <p>
          Здесь появятся сообщения, взаимные совпадения, решения по объявлениям и важные события
          аккаунта.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="notification-toolbar">
        <span className="muted">
          {unread > 0 ? `${unread} непрочитанных` : "Все уведомления прочитаны"}
        </span>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => void markAll()}
          disabled={busy || unread === 0}
        >
          <CheckIcon width={15} height={15} /> Отметить всё прочитанным
        </button>
      </div>
      <div className="notification-list">
        {items.map((item) => {
          const link = linkFor(item);
          return (
            <article className={`notification-row${item.read_at ? "" : " unread"}`} key={item.id}>
              <span className="notification-icon">
                <BellIcon width={19} height={19} />
              </span>
              <div className="grow">
                <div className="notification-meta">
                  <span className="chip chip-brand">
                    {categoryLabels[item.category] ?? item.category}
                  </span>
                  <span className="muted small">{formatDateTime(item.created_at)}</span>
                  {!item.read_at && <span className="unread-dot" aria-label="Не прочитано" />}
                </div>
                <h2>{item.title}</h2>
                <p>{item.body}</p>
                {link && (
                  <button
                    type="button"
                    className="text-link notification-link"
                    onClick={() => void openItem(item)}
                  >
                    Перейти
                  </button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </>
  );
}
