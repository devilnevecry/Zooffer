"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "../auth-provider";
import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime, formatPrice } from "@/lib/format";
import type { AdminPaymentDetail } from "@/lib/types";

const statusLabels: Record<string, string> = {
  created: "Создан",
  pending: "Ожидает",
  paid: "Оплачен",
  canceled: "Отменён",
  refunded: "Возврат",
  failed: "Ошибка",
};

export function PaymentDetail({ initial }: { initial: AdminPaymentDetail }) {
  const { user } = useAuth();
  const showToast = useToast();
  const [detail, setDetail] = useState(initial);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const canWrite = user?.role === "superadmin";
  const order = detail.order;

  const refund = async () => {
    if (
      !window.confirm("Оформить возврат? Платные возможности будут отключены сразу после возврата.")
    ) {
      return;
    }
    setBusy(true);
    try {
      const updated = await api<AdminPaymentDetail>(
        `/api/v1/admin/payments/${order.public_id}/refund`,
        { method: "POST", body: { reason: reason.trim() } },
      );
      setDetail(updated);
      setReason("");
      showToast("Возврат оформлен, подписка отключена", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось оформить возврат",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Биллинг</span>
          <h1>Платёж</h1>
          <p className="muted">Заказ {order.public_id}. Детали и события платёжного провайдера.</p>
        </div>
        <Link href="/admin/payments" className="btn btn-ghost btn-sm">
          К списку
        </Link>
      </div>

      <section className="section">
        <dl className="checkout-summary">
          <div>
            <dt>Тариф</dt>
            <dd>{order.plan_code}</dd>
          </div>
          <div>
            <dt>Сумма</dt>
            <dd>{formatPrice(order.amount_kopecks)}</dd>
          </div>
          <div>
            <dt>Статус</dt>
            <dd>{statusLabels[order.status] ?? order.status}</dd>
          </div>
          <div>
            <dt>Провайдер</dt>
            <dd>{order.provider}</dd>
          </div>
          <div>
            <dt>ID у провайдера</dt>
            <dd>{detail.payment_id ?? "—"}</dd>
          </div>
          <div>
            <dt>Создан</dt>
            <dd>{formatDateTime(order.created_at)}</dd>
          </div>
          <div>
            <dt>Оплачен</dt>
            <dd>{order.paid_at ? formatDateTime(order.paid_at) : "—"}</dd>
          </div>
        </dl>

        {order.demo && (
          <p className="tg-hint">Демонстрационный заказ. Реальных списаний по нему не было.</p>
        )}

        {order.status === "paid" && (
          <div className="admin-refund">
            {canWrite ? (
              <>
                <label className="field">
                  <span>Причина возврата</span>
                  <textarea
                    className="input"
                    rows={3}
                    maxLength={400}
                    value={reason}
                    onChange={(event) => setReason(event.target.value)}
                    placeholder="Например: обращение пользователя, дублирующая оплата"
                  />
                </label>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  disabled={busy || reason.trim().length < 3}
                  onClick={() => void refund()}
                >
                  {busy ? "Оформляем…" : "Оформить возврат"}
                </button>
              </>
            ) : (
              <p className="muted small">
                Возврат доступен только суперадминистратору с подтверждённой 2FA.
              </p>
            )}
          </div>
        )}
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">События</span>
            <h2>Уведомления провайдера</h2>
          </div>
        </div>
        <div className="admin-table-scroll">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Событие</th>
                <th>Статус</th>
                <th>Подпись</th>
                <th>Обработано</th>
                <th>Ошибка</th>
              </tr>
            </thead>
            <tbody>
              {detail.events.map((event) => (
                <tr key={`${event.provider_event_id}-${event.created_at}`}>
                  <td>
                    {event.event_type}
                    <small className="admin-table-sub">{event.provider_event_id}</small>
                  </td>
                  <td>{event.status}</td>
                  <td>{event.signature_valid ? "Проверена" : "Не проверена"}</td>
                  <td>{event.processed_at ? formatDateTime(event.processed_at) : "—"}</td>
                  <td>{event.error ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {detail.events.length === 0 && (
          <p className="muted small">Событий пока нет: платёж ещё не подтверждён.</p>
        )}
      </section>
    </>
  );
}
