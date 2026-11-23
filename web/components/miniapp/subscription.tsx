"use client";

import { useCallback } from "react";

import { SubscriptionManager } from "../subscription-manager";
import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import type { PlanList, StarsInvoice, SubscriptionState } from "@/lib/types";

import { useTelegram } from "./telegram";
import { MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

const fallback: SubscriptionState = {
  status: "none",
  plan_code: null,
  plan_name: null,
  current_period_end: null,
  cancel_at_period_end: false,
  entitlements: [],
  quota_limit: 0,
  quota_unlimited: false,
  payments_available: false,
  payments_demo: false,
  payment_provider: "telegram_stars",
};

export function MiniSubscription() {
  const state = useMiniApi<SubscriptionState>("/api/v1/billing/subscription");
  const plans = useMiniApi<PlanList>("/api/v1/public/plans");
  const { openInvoice } = useTelegram();
  const showToast = useToast();

  const buyStars = useCallback(
    async (planCode: string) => {
      try {
        const invoice = await api<StarsInvoice>("/api/v1/billing/stars/invoice", {
          method: "POST",
          body: { plan_code: planCode },
        });
        const status = await openInvoice(invoice.invoice_url);
        if (status === "paid") {
          showToast("Оплата получена. Подписка активирована.", "success");
          state.reload();
        } else if (status === "cancelled") {
          showToast("Оплата отменена.", "default");
        } else if (status === "failed") {
          showToast("Telegram не смог провести оплату. Попробуйте ещё раз.", "error");
        }
      } catch (err) {
        showToast(
          err instanceof ClientApiError ? err.message : "Не удалось создать счёт в Stars",
          "error",
        );
      }
    },
    [openInvoice, showToast, state],
  );

  if (!state.data && state.loading) return <MiniLoading label="Загружаем подписку…" />;
  if (state.error && !state.data) {
    return <MiniError message={state.error} onRetry={state.reload} />;
  }

  const current = state.data ?? fallback;

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Zooffer Plus"
        title="Подписка"
        lead="План, дневной лимит показов и управление подпиской."
      />

      {!current.payments_available && (
        <p className="tg-hint">
          Оплата в Telegram Stars сейчас недоступна. Списаний нет. Напишите в поддержку, если
          проблема повторяется.
        </p>
      )}

      {plans.error && !plans.data && (
        <p className="muted small">Не удалось загрузить тарифы: {plans.error}</p>
      )}

      <SubscriptionManager
        initial={current}
        plans={plans.data?.items ?? []}
        legalPath="/legal/offer"
        onStarsInvoice={current.payments_available ? buyStars : undefined}
        unavailableNote="Оплата в Telegram Stars пока недоступна. Списаний нет, внешние платёжные ссылки для цифровых товаров в Telegram не используются."
      />
    </div>
  );
}
