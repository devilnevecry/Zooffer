"use client";

import Link from "next/link";

import { HeartIcon, PawIcon } from "../icons";
import { formatDateTime, initials } from "@/lib/format";
import type { ConversationSummary } from "@/lib/types";

import { MiniEmpty, MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

export function MiniChats() {
  const { data, loading, error, reload } = useMiniApi<{ items: ConversationSummary[] }>(
    "/api/v1/conversations",
  );

  if (loading && !data) return <MiniLoading label="Загружаем переписки…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;

  const items = data?.items ?? [];
  const unread = items.reduce((total, chat) => total + chat.unread_count, 0);

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Общение"
        title="Чаты"
        lead="Переписка хранится на сервере и доступна на сайте, в боте и Mini App."
        action={
          <Link href="/tg/matches" className="tg-icon-link" aria-label="Взаимные совпадения">
            <HeartIcon width={18} height={18} />
          </Link>
        }
      />

      {unread > 0 && (
        <p className="tg-unread-line">
          {unread} {unread === 1 ? "непрочитанное сообщение" : "непрочитанных сообщений"}
        </p>
      )}

      {items.length === 0 ? (
        <MiniEmpty
          title="Переписок пока нет"
          text="Напишите владельцу из объявления или дождитесь взаимного совпадения — диалог появится здесь."
          href="/tg/search"
          action="Смотреть объявления"
        />
      ) : (
        <div className="chat-index">
          {items.map((chat) => (
            <Link
              href={`/tg/chats/${chat.public_id}`}
              className="chat-index-row"
              key={chat.public_id}
            >
              <span className="chat-index-avatar">
                {chat.listing?.primary_photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={chat.listing.primary_photo_url} alt="" />
                ) : chat.listing ? (
                  <PawIcon width={24} height={24} />
                ) : (
                  initials(chat.counterpart.display_name)
                )}
              </span>
              <span className="grow">
                <span className="chat-item-top">
                  <strong>{chat.counterpart.display_name ?? "Владелец"}</strong>
                  <span className="muted small">
                    {chat.last_message_at ? formatDateTime(chat.last_message_at) : ""}
                  </span>
                </span>
                <span className="chat-index-listing">
                  {chat.listing
                    ? `${chat.listing.animal_name} · ${chat.listing.title}`
                    : "Взаимное совпадение"}
                </span>
                <span className="chat-item-preview">
                  {chat.last_message
                    ? `${chat.last_message.mine ? "Вы: " : ""}${chat.last_message.body}`
                    : "Диалог открыт — напишите первым"}
                </span>
              </span>
              {chat.unread_count > 0 && (
                <span className="chat-unread">{chat.unread_count}</span>
              )}
              {chat.blocked && <span className="chip chip-danger">Блок</span>}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
