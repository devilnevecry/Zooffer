"use client";

import { useState } from "react";

import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime } from "@/lib/format";
import type { AdminSupportTicket, AdminSupportList } from "@/lib/types";

const statusLabels: Record<string, string> = {
  open: "Открыто",
  pending: "В работе",
  resolved: "Решено",
  closed: "Закрыто",
};

export function SupportQueue({ initial }: { initial: AdminSupportList }) {
  const showToast = useToast();
  const [items, setItems] = useState(initial.items);
  const [openId, setOpenId] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const [status, setStatus] = useState("resolved");
  const [saving, setSaving] = useState(false);

  const openTicket = (ticket: AdminSupportTicket) => {
    setOpenId(ticket.public_id);
    setReply("");
    setStatus(ticket.status === "open" ? "resolved" : ticket.status);
  };

  const submit = async (event: React.FormEvent, ticket: AdminSupportTicket) => {
    event.preventDefault();
    if (reply.trim().length === 0) {
      showToast("Напишите ответ", "error");
      return;
    }
    setSaving(true);
    try {
      const updated = await api<AdminSupportTicket>(
        `/api/v1/admin/support/${ticket.public_id}/reply`,
        {
          method: "POST",
          body: { message: reply.trim(), status },
        },
      );
      setItems((current) =>
        current.map((item) => (item.public_id === updated.public_id ? updated : item)),
      );
      setOpenId(null);
      setReply("");
      showToast("Ответ сохранён", "success");
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось отправить ответ", "error");
    } finally {
      setSaving(false);
    }
  };

  if (items.length === 0) {
    return (
      <div className="empty-state compact-empty">
        <h2>Обращений нет</h2>
        <p>Пользователи пока не писали в поддержку.</p>
      </div>
    );
  }

  return (
    <div className="admin-card-list">
      {items.map((ticket) => (
        <article className="admin-report-card" key={ticket.public_id}>
          <div className="admin-listing-head">
            <div>
              <h2>{ticket.subject}</h2>
              <p className="muted small">
                {ticket.user_name ?? "Пользователь"} · {ticket.channel} ·{" "}
                {formatDateTime(ticket.updated_at)}
              </p>
            </div>
            <span className={`chip admin-report-${ticket.status}`}>
              {statusLabels[ticket.status] ?? ticket.status}
            </span>
          </div>
          {ticket.last_message && <p className="admin-report-details">{ticket.last_message}</p>}
          {openId === ticket.public_id ? (
            <form onSubmit={(event) => void submit(event, ticket)}>
              <div className="field">
                <label htmlFor={`reply-${ticket.public_id}`}>Ответ</label>
                <textarea
                  id={`reply-${ticket.public_id}`}
                  className="textarea"
                  rows={4}
                  maxLength={4000}
                  value={reply}
                  onChange={(event) => setReply(event.target.value)}
                  placeholder="Ответ будет сохранён в обращении"
                />
              </div>
              <div className="inline-field">
                <select
                  className="select"
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  aria-label="Статус обращения"
                >
                  {Object.entries(statusLabels).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
                  {saving ? "Сохраняем…" : "Отправить ответ"}
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => setOpenId(null)}
                >
                  Отмена
                </button>
              </div>
              <p className="field-hint">
                Доставка e-mail и Telegram-сообщений зависит от настроенных каналов.
                Ответ сохраняется в обращении в любом случае.
              </p>
            </form>
          ) : (
            <div className="btn-row">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => openTicket(ticket)}
              >
                Ответить
              </button>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
