"use client";

import Link from "next/link";
import { useState } from "react";

import { CheckIcon, ShieldIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDate, formatPrice } from "@/lib/format";
import type { Plan, SubscriptionState } from "@/lib/types";

const entitlementLabels: Record<string, string> = {
  unlimited_swipes: "Неограниченные свайпы",
  undo: "Отмена последнего свайпа",
  see_who_liked: "Кто меня лайкнул",
  boost: "Поднятие объявлений",
  extended_photos: "До 20 фотографий",
  priority_moderation: "Приоритетная проверка",
  ad_free: "Без партнёрского блока",
};

export function SubscriptionManager({
  initial,
  plans,
  legalPath = "/legal/offer",
}: {
  initial: SubscriptionState;
  plans: Plan[];
  legalPath?: string;
}) {
  const showToast = useToast();
  const [state, setState] = useState(initial);
  const [busy, setBusy] = useState(false);

  const cancel = async () => {
    if (
      !window.confirm(
        "Отменить продление подписки? Доступ сохранится до конца оплаченного периода.",
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      const updated = await api<SubscriptionState>("/api/v1/billing/cancel", { method: "POST" });
      setState(updated);
      showToast("Автопродление отменено", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось отменить подписку",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  const active = state.status === "active" || state.status === "past_due";

  return (
    <>
      <section className={`subscription-hero${active ? " active" : ""}`}>
        <div>
          <span className="eyebrow">Текущий план</span>
          <h2>{state.plan_name ?? "Бесплатный"}</h2>
          <p className="muted">
            {active && state.current_period_end
              ? state.cancel_at_period_end
                ? `Подписка действует до ${formatDate(state.current_period_end)}, автопродление отключено.`
                : `Подписка действует до ${formatDate(state.current_period_end)} и продлится автоматически.`
              : "Базовый доступ: подбор, объявления, избранное и переписка."}
          </p>
        </div>
        <div className="subscription-quota">
          <strong>
            {state.quota_unlimited ? "∞" : state.quota_limit}
          </strong>
          <span>{state.quota_unlimited ? "свайпов без лимита" : "свайпов в день"}</span>
        </div>
        {active && !state.cancel_at_period_end && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void cancel()}
            disabled={busy}
          >
            {busy ? "Отменяем…" : "Отменить автопродление"}
          </button>
        )}
      </section>

      {!state.payments_available && (
        <div className="notice warn">
          <ShieldIcon width={18} height={18} />
          <span>
            Онлайн-оплата пока недоступна: не настроены платёжные реквизиты. Цены ниже —
            демонстрационные и будут изменены до запуска. Оформить платный план сейчас
            нельзя, списаний не происходит.
          </span>
        </div>
      )}

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Тарифы</span>
            <h2>Больше возможностей</h2>
            <p>Все цены указаны в рублях. Условия и правила отмены — в оферте.</p>
          </div>
        </div>
        <div className="plan-grid">
          <article className="plan-card">
            <h3>Бесплатно</h3>
            <p className="plan-price">0 ₽</p>
            <p className="muted">Базовый доступ навсегда</p>
            <ul className="plan-list">
              <li>
                <CheckIcon width={15} height={15} /> {state.quota_limit} свайпов в день
              </li>
              <li>
                <CheckIcon width={15} height={15} /> Объявления и избранное
              </li>
              <li>
                <CheckIcon width={15} height={15} /> Переписка и совпадения
              </li>
            </ul>
            <span className="btn btn-secondary btn-sm plan-disabled" aria-disabled="true">
              {active ? "Базовый уровень" : "Текущий план"}
            </span>
          </article>

          {plans.map((plan) => {
            const current = state.plan_code === plan.code && active;
            return (
              <article className="plan-card featured" key={plan.code}>
                {plan.is_placeholder_price && (
                  <span className="plan-flag">Цена до запуска</span>
                )}
                <h3>{plan.name}</h3>
                <p className="plan-price">{formatPrice(plan.price_kopecks)}</p>
                <p className="muted">
                  за {plan.period_days} дней
                  {plan.stars_amount ? ` · ${plan.stars_amount} Stars` : ""}
                </p>
                <p>{plan.description}</p>
                <ul className="plan-list">
                  {plan.entitlements.map((code) => (
                    <li key={code}>
                      <CheckIcon width={15} height={15} />{" "}
                      {entitlementLabels[code] ?? code}
                    </li>
                  ))}
                </ul>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={!state.payments_available || current}
                >
                  {current
                    ? "Подключено"
                    : state.payments_available
                      ? "Перейти к оплате"
                      : "Оплата недоступна"}
                </button>
              </article>
            );
          })}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Важно</span>
            <h2>Оплата и возврат</h2>
          </div>
        </div>
        <div className="legal-summary">
          <p>
            Подписка не продлевается без вашего согласия. Отменить автопродление можно
            в этой комнате в любой момент — доступ сохранится до конца оплаченного
            периода.
          </p>
          <p>
            Платёжные данные вводятся только на стороне платёжного провайдера. Zooffer
            не хранит номера карт. Чеки и возвраты регулируются офертой и
            законодательством РФ.
          </p>
          <Link href={legalPath} className="text-link">
            Условия подписки и возврата
          </Link>
        </div>
      </section>
    </>
  );
}
