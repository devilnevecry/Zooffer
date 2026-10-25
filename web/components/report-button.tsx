"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { FlagIcon } from "./icons";
import { Modal } from "./modal";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";

type ReportTarget = "listing" | "animal" | "message" | "user";

const REASONS: { value: string; label: string }[] = [
  { value: "spam", label: "Спам или реклама" },
  { value: "scam", label: "Мошенничество, предоплата или обман" },
  { value: "cruelty", label: "Жестокое обращение с животным" },
  { value: "prohibited", label: "Запрещённый товар или контент" },
  { value: "contacts", label: "Контакты опубликованы без согласия" },
  { value: "other", label: "Другое" },
];

export function ReportButton({
  targetType,
  targetId,
  label = "Пожаловаться",
  className = "btn btn-ghost btn-sm",
}: {
  targetType: ReportTarget;
  targetId: string;
  label?: string;
  className?: string;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const showToast = useToast();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("spam");
  const [details, setDetails] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const openDialog = () => {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setError("");
    setOpen(true);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSending(true);
    setError("");
    try {
      await api("/api/v1/reports", {
        method: "POST",
        body: {
          target_type: targetType,
          target_public_id: targetId,
          reason,
          details: details.trim() || null,
        },
      });
      setOpen(false);
      setDetails("");
      showToast("Жалоба отправлена. Модераторы проверят материал.");
    } catch (err) {
      setError(
        err instanceof ClientApiError
          ? err.message
          : "Не удалось отправить жалобу. Попробуйте ещё раз.",
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button type="button" className={className} onClick={openDialog}>
        <FlagIcon width={15} height={15} /> {label}
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Пожаловаться модератору">
        <form onSubmit={submit}>
          <p className="modal-lead">
            Расскажите, что не так. Жалоба не отправится владельцу, а попадёт в очередь модерации
            Zooffer.
          </p>
          <div className="field">
            <label htmlFor="report-reason">Причина</label>
            <select
              id="report-reason"
              className="input"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            >
              {REASONS.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="report-details">Подробности (необязательно)</label>
            <textarea
              id="report-details"
              className="textarea"
              value={details}
              onChange={(event) => setDetails(event.target.value)}
              maxLength={1000}
              rows={4}
              placeholder="Что произошло?"
            />
            <span className="field-hint">{details.length} / 1000</span>
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="btn-row">
            <button type="submit" className="btn btn-primary" disabled={sending}>
              {sending ? "Отправляем…" : "Отправить жалобу"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>
              Отмена
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
