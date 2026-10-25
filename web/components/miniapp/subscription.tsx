"use client";

import { SubscriptionManager } from "../subscription-manager";
import type { PlanList, SubscriptionState } from "@/lib/types";

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
  payment_provider: "fake",
};

export function MiniSubscription() {
  const state = useMiniApi<SubscriptionState>("/api/v1/billing/subscription");
  const plans = useMiniApi<PlanList>("/api/v1/public/plans");

  if (!state.data && state.loading) return <MiniLoading label="Загружаем подписку…" />;
  if (state.error && !state.data) {
    return <MiniError message={state.error} onRetry={state.reload} />;
  }

  const current = state.data ?? fallback;
  // Digital goods inside Telegram require Stars. Until the Stars flow exists,
  // the Mini App must not open a card checkout or an external payment link.
  const telegramState: SubscriptionState = {
    ...current,
    payments_available: false,
    payments_demo: false,
  };

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Zooffer Plus"
        title="Подписка"
        lead="План, дневной лимит показов и управление подпиской."
      />

      {!current.payments_available && (
        <p className="tg-hint">
          Telegram Stars появится в Mini App после подключения платёжного провайдера.
          Сейчас списаний нет.
        </p>
      )}

      {plans.error && !plans.data && (
        <p className="muted small">Не удалось загрузить тарифы: {plans.error}</p>
      )}

      <SubscriptionManager
        initial={telegramState}
        plans={plans.data?.items ?? []}
        legalPath="/legal/offer"
        unavailableNote="Покупка подписки в Telegram Stars пока недоступна. Списаний нет, внешние платёжные ссылки для цифровых товаров в Telegram не используются."
      />
    </div>
  );
}
