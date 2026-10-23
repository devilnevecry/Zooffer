"use client";

import { useCallback, useState } from "react";

import { Modal } from "../modal";
import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime } from "@/lib/format";
import type { AdminReport, AdminReportList } from "@/lib/types";

const statuses = [
  { value: "open", label: "Открытые" },
  { value: "in_review", label: "На проверке" },
  { value: "resolved", label: "Решённые" },
  { value: "dismissed", label: "Отклонённые" },
  { value: "", label: "Все" },
];

const reasonLabels: Record<string, string> = {
  spam: "Спам или реклама",
  scam: "Мошенничество",
  cruelty: "Жестокое обращение",
  prohibited: "Запрещённый контент",
  contacts: "Контакты без согласия",
  other: "Другое",
};

const targetLabels: Record<string, string> = {
  listing: "Объявление",
  animal: "Животное",
  message: "Сообщение",
  user: "Пользователь",
};

const statusLabels: Record<string, string> = {
  open: "Открыта",
  in_review: "На проверке",
  resolved: "Решена",
  dismissed: "Отклонена",
};

export function ReportQueue({ initial }: { initial: AdminReportList }) {
  const showToast = useToast();
  const [items, setItems] = useState(initial.items);
  const [status, setStatus] = useState("open");
  const [loading, setLoading] = useState(false);
  const [target, setTarget] = useState<{ report: AdminReport; status: string } | null>(null);
  const [resolution, setResolution] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async (nextStatus: string) => {
    setLoading(true);
    try {
      const query = nextStatus ? `?status=${nextStatus}` : "";
      const data = await api<AdminReportList>(`/api/v1/admin/reports${query}`);
      setItems(data.items);
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось загрузить жалобы", "error");
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  const openDecision = (report: AdminReport, nextStatus: string) => {
    setTarget({ report, status: nextStatus });
    setResolution(nextStatus === "resolved" ? "Материал проверен, меры приняты" : "");
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!target) return;
    if (resolution.trim().length < 3) {
      showToast("Опишите решение", "error");
      return;
    }
    setSaving(true);
    try {
      const updated = await api<AdminReport>(`/api/v1/admin/reports/${target.report.id}`, {
        method: "PATCH",
        body: { status: target.status, resolution: resolution.trim() },
      });
      setTarget(null);
      showToast("Статус жалобы обновлён", "success");
      if (status && status !== updated.status) {
        setItems((current) => current.filter((item) => item.id !== updated.id));
      } else {
        setItems((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        );
      }
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось обновить жалобу", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="admin-toolbar">
        <div className="admin-tabs" role="tablist" aria-label="Статус жалоб">
          {statuses.map((item) => (
            <button
              key={item.value || "all"}
              type="button"
              role="tab"
              aria-selected={status === item.value}
              className={status === item.value ? "active" : undefined}
              onClick={() => {
                setStatus(item.value);
                void load(item.value);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="muted small">Загружаем…</p>}

      {items.length === 0 ? (
        <div className="empty-state compact-empty">
          <h2>Жалоб нет</h2>
          <p>В этой категории пока пусто.</p>
        </div>
      ) : (
        <div className="admin-card-list">
          {items.map((report) => (
            <article className="admin-report-card" key={report.id}>
              <div className="admin-listing-head">
                <div>
                  <h2>
                    {targetLabels[report.target_type] ?? report.target_type}:{" "}
                    {reasonLabels[report.reason] ?? report.reason}
                  </h2>
                  <p className="muted small">
                    {formatDateTime(report.created_at)} · автор жалобы:{" "}
                    {report.reporter_name ?? "удалён или анонимен"}
                  </p>
                </div>
                <span className={`chip admin-report-${report.status}`}>
                  {statusLabels[report.status] ?? report.status}
                </span>
              </div>
              {report.details && <p className="admin-report-details">{report.details}</p>}
              <p className="muted small">
                Объект: <code>{report.target_public_id}</code>
              </p>
              {report.resolved_at && (
                <p className="muted small">Закрыта: {formatDateTime(report.resolved_at)}</p>
              )}
              {report.status !== "resolved" && report.status !== "dismissed" && (
                <div className="btn-row">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => openDecision(report, "in_review")}
                  >
                    Взять в работу
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => openDecision(report, "resolved")}
                  >
                    Решить
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => openDecision(report, "dismissed")}
                  >
                    Отклонить
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      <Modal open={target !== null} onClose={() => setTarget(null)} title="Решение по жалобе">
        <form onSubmit={submit}>
          <p className="modal-lead">
            Решение сохранится в журнале. Для жалоб на сообщения проверьте переписку в
            поддержке, если нужен контекст.
          </p>
          <div className="field">
            <label htmlFor="report-resolution">Комментарий</label>
            <textarea
              id="report-resolution"
              className="textarea"
              rows={4}
              maxLength={1000}
              value={resolution}
              onChange={(event) => setResolution(event.target.value)}
              placeholder="Что проверено и какие меры приняты"
            />
          </div>
          <div className="btn-row">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Сохраняем…" : "Сохранить"}
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
