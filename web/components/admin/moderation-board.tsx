"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { useToast } from "../toast-provider";
import { Modal } from "../modal";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime, formatListingPrice, purposeLabel, speciesLabel } from "@/lib/format";
import type { AdminListing, AdminListingList } from "@/lib/types";

const statuses = [
  { value: "pending_moderation", label: "На проверке" },
  { value: "published", label: "Опубликованные" },
  { value: "rejected", label: "Отклонённые" },
  { value: "", label: "Все" },
];

const statusLabels: Record<string, string> = {
  draft: "Черновик",
  pending_moderation: "На проверке",
  published: "Опубликовано",
  rejected: "Отклонено",
  archived: "В архиве",
  expired: "Истекло",
};

export function ModerationBoard({ initial }: { initial: AdminListingList }) {
  const showToast = useToast();
  const [items, setItems] = useState(initial.items);
  const [total, setTotal] = useState(initial.total);
  const [status, setStatus] = useState("pending_moderation");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [target, setTarget] = useState<{
    listing: AdminListing;
    action: "approve" | "reject";
  } | null>(null);
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(
    async (nextStatus: string, nextQuery: string) => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        if (nextStatus) params.set("status", nextStatus);
        if (nextQuery.trim()) params.set("q", nextQuery.trim());
        const data = await api<AdminListingList>(`/api/v1/admin/listings?${params.toString()}`);
        setItems(data.items);
        setTotal(data.total);
      } catch (err) {
        showToast(
          err instanceof ClientApiError ? err.message : "Не удалось загрузить очередь",
          "error",
        );
      } finally {
        setLoading(false);
      }
    },
    [showToast],
  );

  const openDecision = (listing: AdminListing, action: "approve" | "reject") => {
    setTarget({ listing, action });
    setReason(action === "approve" ? "Проверено вручную" : "");
  };

  const submitDecision = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!target) return;
    if (reason.trim().length < 3) {
      showToast("Укажите причину решения", "error");
      return;
    }
    setSaving(true);
    try {
      const updated = await api<AdminListing>(
        `/api/v1/admin/moderation/listings/${target.listing.public_id}`,
        {
          method: "POST",
          body: { action: target.action, reason: reason.trim() },
        },
      );
      setTarget(null);
      showToast(
        target.action === "approve" ? "Объявление опубликовано" : "Объявление отклонено",
        "success",
      );
      if (status === "pending_moderation") {
        setItems((current) => current.filter((item) => item.public_id !== updated.public_id));
        setTotal((value) => Math.max(0, value - 1));
      } else {
        setItems((current) =>
          current.map((item) => (item.public_id === updated.public_id ? updated : item)),
        );
      }
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось применить решение",
        "error",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="admin-toolbar">
        <div className="admin-tabs" role="tablist" aria-label="Статус объявлений">
          {statuses.map((item) => (
            <button
              key={item.value || "all"}
              type="button"
              role="tab"
              aria-selected={status === item.value}
              className={status === item.value ? "active" : undefined}
              onClick={() => {
                setStatus(item.value);
                setQuery("");
                void load(item.value, "");
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
        <form
          className="admin-search"
          onSubmit={(event) => {
            event.preventDefault();
            void load(status, query);
          }}
        >
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Название или кличка"
            aria-label="Поиск объявлений"
          />
          <button type="submit" className="btn btn-secondary btn-sm" disabled={loading}>
            {loading ? "Ищем…" : "Найти"}
          </button>
        </form>
      </div>

      <p className="muted small">
        Найдено: {total}.{" "}
        {status === "pending_moderation"
          ? "Сначала проверяйте объявления с жалобами и контактами в тексте."
          : ""}
      </p>

      {items.length === 0 ? (
        <div className="empty-state compact-empty">
          <h2>Очередь пуста</h2>
          <p>Объявлений с этим статусом нет.</p>
        </div>
      ) : (
        <div className="admin-card-list">
          {items.map((listing) => (
            <article className="admin-listing-card" key={listing.public_id}>
              <div className="admin-listing-photo">
                {listing.photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={listing.photo_url} alt={listing.animal_name} />
                ) : (
                  <span>Без фото</span>
                )}
              </div>
              <div className="admin-listing-main">
                <div className="admin-listing-head">
                  <div>
                    <h2>{listing.title}</h2>
                    <p>
                      {listing.animal_name} · {speciesLabel(listing.species)} ·{" "}
                      {purposeLabel(listing.purpose)}
                    </p>
                  </div>
                  <span className={`chip admin-status-${listing.status}`}>
                    {statusLabels[listing.status] ?? listing.status}
                  </span>
                </div>
                <dl className="admin-meta">
                  <div>
                    <dt>Владелец</dt>
                    <dd>{listing.owner_name ?? "Владелец"}</dd>
                  </div>
                  <div>
                    <dt>Город</dt>
                    <dd>{listing.city_name ?? "Не указан"}</dd>
                  </div>
                  <div>
                    <dt>Цена</dt>
                    <dd>{formatListingPrice(listing.purpose, listing.price_kopecks, false)}</dd>
                  </div>
                  <div>
                    <dt>Создано</dt>
                    <dd>{formatDateTime(listing.created_at)}</dd>
                  </div>
                  <div>
                    <dt>Качество</dt>
                    <dd>{listing.quality_score}%</dd>
                  </div>
                </dl>
                {listing.moderation_reason && (
                  <p className="notice compact-notice">
                    <strong>Причина:</strong> {listing.moderation_reason}
                  </p>
                )}
                <div className="btn-row">
                  {listing.status === "published" && (
                    <Link href={`/listing/${listing.slug}`} className="btn btn-ghost btn-sm">
                      Открыть
                    </Link>
                  )}
                  {listing.status !== "rejected" && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => openDecision(listing, "reject")}
                    >
                      Отклонить
                    </button>
                  )}
                  {listing.status !== "published" && (
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => openDecision(listing, "approve")}
                    >
                      Одобрить
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <Modal
        open={target !== null}
        onClose={() => setTarget(null)}
        title={target?.action === "approve" ? "Опубликовать объявление" : "Отклонить объявление"}
      >
        <form onSubmit={submitDecision}>
          <p className="modal-lead">
            {target?.action === "approve"
              ? "Объявление станет публичным и появится в поиске. Убедитесь, что фото и текст не нарушают правила."
              : "Причина будет сохранена в журнале модерации и видна владельцу в статусе объявления."}
          </p>
          <div className="field">
            <label htmlFor="moderation-reason">Причина</label>
            <textarea
              id="moderation-reason"
              className="textarea"
              rows={4}
              maxLength={1000}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              placeholder={
                target?.action === "approve"
                  ? "Проверено вручную: фото, текст и условия корректны"
                  : "Опишите нарушение"
              }
            />
          </div>
          <div className="btn-row">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Сохраняем…" : "Подтвердить"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setTarget(null)}>
              Отмена
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
