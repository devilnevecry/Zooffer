"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ArrowIcon, ChatIcon, PawIcon, ShieldIcon } from "./icons";
import { ReportButton } from "./report-button";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime, initials } from "@/lib/format";
import type { ConversationDetail, MessagePageView } from "@/lib/types";

const POLL_MS = 4_000;

export function ChatPanel({
  initial,
  basePath = "/account",
  listingPath = "/listing",
  compact = false,
}: {
  initial: ConversationDetail | null;
  basePath?: string;
  listingPath?: string;
  compact?: boolean;
}) {
  const showToast = useToast();
  const [detail, setDetail] = useState(initial);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [blocked, setBlocked] = useState(initial?.conversation.blocked ?? false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const conversationId = initial?.conversation.public_id;

  const load = useCallback(async () => {
    if (!conversationId) return;
    try {
      const fresh = await api<ConversationDetail>(`/api/v1/conversations/${conversationId}`);
      setDetail(fresh);
      setBlocked(fresh.conversation.blocked);
    } catch {
      // Temporary network failures should not wipe the visible conversation.
    }
  }, [conversationId]);

  useEffect(() => {
    if (!conversationId) return;
    void api(`/api/v1/conversations/${conversationId}/read`, { method: "POST" }).catch(
      () => undefined,
    );
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [conversationId, load]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [detail?.messages.length]);

  const sendText = async () => {
    if (!conversationId || !text.trim() || sending) return;
    setSending(true);
    try {
      await api(`/api/v1/conversations/${conversationId}/messages`, {
        method: "POST",
        body: { body: text.trim() },
      });
      setText("");
      await load();
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось отправить сообщение", "error");
    } finally {
      setSending(false);
    }
  };

  const send = (event: React.FormEvent) => {
    event.preventDefault();
    void sendText();
  };

  const loadOlder = async () => {
    if (!conversationId || !detail?.next_cursor || loadingOlder) return;
    setLoadingOlder(true);
    try {
      const page = await api<MessagePageView>(
        `/api/v1/conversations/${conversationId}/messages?cursor=${encodeURIComponent(detail.next_cursor)}`,
      );
      setDetail((current) =>
        current
          ? {
              ...current,
              messages: [...page.items, ...current.messages],
              next_cursor: page.next_cursor,
              has_more: page.has_more,
            }
          : current,
      );
    } catch {
      showToast("Не удалось загрузить историю", "error");
    } finally {
      setLoadingOlder(false);
    }
  };

  const toggleBlock = async () => {
    if (!conversationId) return;
    const nextBlocked = !blocked;
    if (
      nextBlocked &&
      !window.confirm(
        "Заблокировать пользователя? Он не сможет писать вам, а вы — ему, пока блокировка не будет снята.",
      )
    ) {
      return;
    }
    try {
      await api(`/api/v1/conversations/${conversationId}/block`, {
        method: nextBlocked ? "POST" : "DELETE",
      });
      setBlocked(nextBlocked);
      showToast(nextBlocked ? "Пользователь заблокирован" : "Блокировка снята");
      await load();
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось изменить блокировку", "error");
    }
  };

  if (!detail) {
    return (
      <div className="empty-state">
        <ChatIcon width={44} height={44} />
        <h2>Диалог не найден</h2>
        <p>Возможно, он был удалён или у вас нет доступа к этой переписке.</p>
        <Link href={`${basePath}/chats`} className="btn btn-secondary">
          Все сообщения
        </Link>
      </div>
    );
  }

  const conversation = detail.conversation;

  return (
    <div className={`chat-page${compact ? " chat-page-compact" : ""}`}>
      {!compact && (
        <nav className="breadcrumbs" aria-label="Навигация">
          <Link href={`${basePath}/chats`}>Сообщения</Link>
          <span aria-hidden="true">/</span>
          <span>{conversation.counterpart.display_name ?? "Владелец"}</span>
        </nav>
      )}

      {compact && (
        <header className="chat-compact-head">
          <span className="chat-index-avatar">
            {conversation.listing?.primary_photo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={conversation.listing.primary_photo_url} alt="" />
            ) : (
              initials(conversation.counterpart.display_name)
            )}
          </span>
          <span className="grow">
            <strong>{conversation.counterpart.display_name ?? "Владелец"}</strong>
            <small>
              {conversation.listing
                ? `${conversation.listing.animal_name} · ${conversation.listing.title}`
                : "Взаимное совпадение"}
            </small>
          </span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void toggleBlock()}
          >
            {blocked ? "Разблокировать" : "Блок"}
          </button>
        </header>
      )}

      <div className={`chat-layout${compact ? " chat-layout-compact" : ""}`}>
        {!compact && (
          <aside className="chat-context">
            <div className="chat-context-head">
              <span className="chat-index-avatar">
                {conversation.listing?.primary_photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={conversation.listing.primary_photo_url} alt="" />
                ) : (
                  initials(conversation.counterpart.display_name)
                )}
              </span>
              <div>
                <strong>{conversation.counterpart.display_name ?? "Владелец"}</strong>
                <p>
                  {conversation.conversation_type === "match"
                    ? "Взаимное совпадение"
                    : "Запрос по объявлению"}
                </p>
              </div>
            </div>
            {conversation.listing && (
              <Link
                href={`${listingPath}/${conversation.listing.slug}`}
                className="chat-context-listing"
              >
                {conversation.listing.primary_photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={conversation.listing.primary_photo_url} alt="" />
                ) : (
                  <span className="chat-index-avatar">
                    <PawIcon width={22} height={22} />
                  </span>
                )}
                <span>
                  <strong>{conversation.listing.animal_name}</strong>
                  <small>{conversation.listing.title}</small>
                </span>
                <ArrowIcon width={16} height={16} />
              </Link>
            )}
            <div className="privacy-note">
              <ShieldIcon width={18} height={18} />
              <span>
                Не отправляйте предоплату и коды из SMS. Контакты передавайте только
                когда сами решите это сделать.
              </span>
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void toggleBlock()}
            >
              {blocked ? "Снять блокировку" : "Заблокировать пользователя"}
            </button>
          </aside>
        )}

        <section
          className="chat-pane"
          aria-label={`Переписка с ${conversation.counterpart.display_name ?? "владельцем"}`}
        >
          {!compact && (
            <header className="chat-pane-head">
              <div className="grow">
                <strong>{conversation.counterpart.display_name ?? "Владелец"}</strong>
                <div className="muted small">
                  {blocked
                    ? "Переписка ограничена блокировкой"
                    : "Ответ обычно приходит в течение дня"}
                </div>
              </div>
              {conversation.listing && (
                <Link
                  href={`${listingPath}/${conversation.listing.slug}`}
                  className="btn btn-secondary btn-sm"
                >
                  Объявление
                </Link>
              )}
            </header>
          )}

          <div className="chat-scroll" ref={scrollRef} aria-live="polite">
            {detail.has_more && (
              <button
                type="button"
                className="btn btn-ghost btn-sm chat-older"
                onClick={() => void loadOlder()}
                disabled={loadingOlder}
              >
                {loadingOlder ? "Загружаем…" : "Показать более ранние"}
              </button>
            )}
            {detail.messages.map((message) => (
              <div className={`bubble${message.mine ? " mine" : ""}`} key={message.id}>
                {message.body}
                <span className="bubble-time">{formatDateTime(message.created_at)}</span>
                {!message.mine && (
                  <ReportButton
                    targetType="message"
                    targetId={message.id}
                    label="Пожаловаться"
                    className="bubble-report"
                  />
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          <form className="composer" onSubmit={send}>
            <label htmlFor="message-body" className="sr-only">
              Сообщение
            </label>
            <textarea
              id="message-body"
              value={text}
              onChange={(event) => setText(event.target.value)}
              maxLength={4000}
              rows={1}
              placeholder={blocked ? "Снимите блокировку, чтобы писать" : "Напишите сообщение…"}
              disabled={blocked || sending}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void sendText();
                }
              }}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={blocked || sending || !text.trim()}
            >
              {sending ? "Отправляем…" : "Отправить"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
