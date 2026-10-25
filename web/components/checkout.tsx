"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ShieldIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime, formatPrice } from "@/lib/format";
import type { BillingOrder } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  created: "Создан",
  pending: "Ожидает оплаты",
  paid: "Оплачен",
  failed: "Ошибка",
  canceled: "Отменён",
  refunded: "Возвращён",
};

export function CheckoutPanel({
  orderId,
  backHref = "/account/subscription",
  backLabel = "Вернуться к подписке",
}: {
  orderId: string;
  backHref?: string;
  backLabel?: string;
}) {
  const showToast = useToast();
  const [order, setOrder] = useState<BillingOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const next = await api<BillingOrder>(`/api/v1/billing/orders/${orderId}`);
      setOrder(next);
      setError(null);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Не удалось загрузить платёж");
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    let active = true;
    api<BillingOrder>(`/api/v1/billing/orders/${orderId}`)
      .then((next) => {
        if (active) {
          setOrder(next);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ClientApiError ? err.message : "Не удалось загрузить платёж");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [orderId]);

  const refresh = async () => {
    setLoading(true);
    await load();
  };

  const confirmDemo = async () => {
    setBusy(true);
    try {
      const next = await api<BillingOrder>(`/api/v1/billing/orders/${orderId}/demo-confirm`, {
        method: "POST",
      });
      setOrder(next);
      showToast("Демо-платёж подтверждён. Подписка активирована.", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось подтвердить платёж",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="checkout-panel">
        <p className="muted">Загружаем платёж…</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="checkout-panel">
        <div className="notice warn">
          <ShieldIcon width={18} height={18} />
          <span>{error ?? "Платёж не найден."}</span>
        </div>
        <Link href={backHref} className="btn btn-secondary">
          {backLabel}
        </Link>
      </div>
    );
  }

  const paid = order.status === "paid";
  const payable = order.status === "created" || order.status === "pending";

  return (
    <div className="checkout-panel">
      {order.demo && payable && (
        <div className="notice warn">
          <ShieldIcon width={18} height={18} />
          <span>
            Демонстрационная оплата. Это не настоящий платёж: деньги не списываются, карта не
            запрашивается. Подтверждение ниже активирует подписку внутри тестового окружения.
          </span>
        </div>
      )}

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
          <dd>{STATUS_LABELS[order.status] ?? order.status}</dd>
        </div>
        <div>
          <dt>Создан</dt>
          <dd>{formatDateTime(order.created_at)}</dd>
        </div>
        <div>
          <dt>Провайдер</dt>
          <dd>{order.provider === "fake" ? "Демо" : order.provider}</dd>
        </div>
      </dl>

      {paid ? (
        <div className="checkout-result success">
          <strong>Подписка активирована</strong>
          <p className="muted">
            Оплата зафиксирована. Платные возможности уже доступны в аккаунте.
          </p>
        </div>
      ) : order.demo && payable ? (
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => void confirmDemo()}
          disabled={busy}
        >
          {busy ? "Подтверждаем…" : "Подтвердить демо-оплату"}
        </button>
      ) : (
        <div className="checkout-result">
          <strong>Ожидаем подтверждение платёжной системы</strong>
          <p className="muted">
            Если оплата уже прошла, обновите статус через минуту. Подписка включится автоматически
            после уведомления провайдера.
          </p>
          <button type="button" className="btn btn-secondary" onClick={() => void refresh()}>
            Обновить статус
          </button>
        </div>
      )}

      <Link href={backHref} className="text-link">
        {backLabel}
      </Link>
    </div>
  );
}
