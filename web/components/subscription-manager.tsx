"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { CheckIcon, ShieldIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDate, formatPrice } from "@/lib/format";
import type { BillingOrder, Plan, SubscriptionState } from "@/lib/types";

const entitlementLabels: Record<string, string> = {
  unlimited_swipes: "♾️ Безлимитные свайпы — дневной лимит снят",
  undo: "↩️ Отмена последнего свайпа",
  see_who_liked: "💗 Кто вас лайкнул",
  boost: "🚀 Поднятие ваших объявлений",
  extended_photos: "🖼 До 20 фотографий в объявлении",
  priority_moderation: "⚡️ Приоритетная проверка объявлений",
  ad_free: "✨ Без партнёрского блока",
};

export function SubscriptionManager({
  initial,
  plans,
  legalPath = "/legal/offer",
  checkoutPath = "/account/subscription/checkout",
  unavailableNote,
  telegramUrl,
  onStarsInvoice,
}: {
  initial: SubscriptionState;
  plans: Plan[];
  legalPath?: string;
  checkoutPath?: string;
  unavailableNote?: string;
  /** Bot deep link used by the website: Stars can only be paid inside Telegram. */
  telegramUrl?: string;
  /** Mini App hook that opens a Telegram Stars invoice. */
  onStarsInvoice?: (planCode: string) => Promise<void>;
}) {
  const showToast = useToast();
  const router = useRouter();
  const [state, setState] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [paying, setPaying] = useState<string | null>(null);

  const starsProvider = state.payment_provider === "telegram_stars";
  const purchaseMode = starsProvider ? (onStarsInvoice ? "stars" : "telegram") : "provider";
  const botUrl =
    telegramUrl ?? process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "https://t.me/";

  const cancel = async () => {
    if (
      !window.confirm(
        "Отменить подписку? Доступ сохранится до конца оплаченного периода, новые платежи не списываются.",
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      const updated = await api<SubscriptionState>("/api/v1/billing/cancel", { method: "POST" });
      setState(updated);
      showToast("Подписка отменена", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось отменить подписку",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  const startCheckout = async (planCode: string) => {
    if (purchaseMode === "telegram") {
      // Digital goods cannot be sold by an external card link inside Telegram,
      // and the website cannot charge Stars: hand the user over to the bot.
      window.open(`${botUrl}?start=buy_${planCode}`, "_blank", "noopener,noreferrer");
      return;
    }
    setPaying(planCode);
    try {
      if (purchaseMode === "stars" && onStarsInvoice) {
        await onStarsInvoice(planCode);
        return;
      }
      const order = await api<BillingOrder>("/api/v1/billing/orders", {
        method: "POST",
        body: { plan_code: planCode },
      });
      if (order.provider !== "fake" && order.confirmation_url) {
        window.location.assign(order.confirmation_url);
        return;
      }
      router.push(`${checkoutPath}?order=${order.public_id}`);
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось создать платёж", "error");
    } finally {
      setPaying(null);
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
                ? `Подписка отменена. Доступ сохранится до ${formatDate(state.current_period_end)} — новых списаний не будет.`
                : `Подписка действует до ${formatDate(state.current_period_end)} Автоматических списаний нет — продление только по новой оплате.`
              : "Базовый доступ: подбор, объявления, избранное и переписка."}
          </p>
        </div>
        <div className="subscription-quota">
          <strong>{state.quota_unlimited ? "∞" : state.quota_limit}</strong>
          <span>{state.quota_unlimited ? "свайпов без лимита" : "свайпов в день"}</span>
        </div>
        {active && !state.cancel_at_period_end && (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void cancel()}
            disabled={busy}
          >
            {busy ? "Отменяем…" : "Отменить подписку"}
          </button>
        )}
      </section>

      {!state.payments_available && (
        <div className="notice warn">
          <ShieldIcon width={18} height={18} />
          <span>
            {unavailableNote ??
              "Онлайн-оплата пока недоступна: не настроены платёжные реквизиты. Оформить платный план сейчас нельзя, списаний не происходит."}
          </span>
        </div>
      )}

      {starsProvider && purchaseMode === "telegram" && (
        <div className="notice">
          <ShieldIcon width={18} height={18} />
          <span>
            Подписка оплачивается в Telegram Stars. На сайте оплата картой не принимается —
            кнопка открывает бота, где счёт оплачивается звёздами.
          </span>
        </div>
      )}

      {state.payments_available && state.payments_demo && (
        <div className="notice warn">
          <ShieldIcon width={18} height={18} />
          <span>
            Включён демонстрационный режим оплаты. Реальные деньги не списываются, карта не
            запрашивается. Такой платёж нужен только для проверки сценария.
          </span>
        </div>
      )}

      <section className="section">
        <div className="section-head">
          <div>
            <span className="eyebrow">Тарифы</span>
            <h2>Больше возможностей</h2>
            <p>
              {starsProvider
                ? "Оплата в Telegram Stars. При апгрейде неиспользованные дни старого тарифа засчитываются в счёт нового — одна подписка, без дублей. Условия и правила отмены — в оферте."
                : "Все цены указаны в рублях. При апгрейде неиспользованные дни старого тарифа засчитываются в счёт нового. Условия и правила отмены — в оферте."}
            </p>
          </div>
        </div>
        <div className="plan-grid">
          <article className="plan-card">
            <h3>Бесплатно</h3>
            <p className="plan-price">0 ₽</p>
            <p className="muted">Базовый доступ навсегда</p>
            <ul className="plan-list">
              <li>
                <CheckIcon width={15} height={15} />{" "}
                {state.quota_unlimited
                  ? "Базовый дневной лимит свайпов"
                  : `${state.quota_limit} свайпов в день`}
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

          {plans
            .filter((plan) => plan.price_kopecks > 0)
            .map((plan) => {
              const current = state.plan_code === plan.code && active;
              return (
                <article className="plan-card featured" key={plan.code}>
                  {plan.is_placeholder_price && <span className="plan-flag">Цена до запуска</span>}
                  <h3>{plan.name}</h3>
                  <p className="plan-price">
                    {starsProvider && plan.stars_amount
                      ? `${plan.stars_amount} ★`
                      : formatPrice(plan.price_kopecks)}
                  </p>
                  <p className="muted">
                    за {plan.period_days} дней
                    {starsProvider && plan.stars_amount
                      ? " · оплата Telegram Stars"
                      : plan.stars_amount
                        ? ` · ${plan.stars_amount} Stars`
                        : ""}
                  </p>
                  <p>{plan.description}</p>
                  <ul className="plan-list">
                    {plan.entitlements.map((code) => (
                      <li key={code}>
                        <CheckIcon width={15} height={15} />{" "}
                        {entitlementLabels[code] ?? code.replace(/_/g, " ")}
                      </li>
                    ))}
                  </ul>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => void startCheckout(plan.code)}
                    disabled={!state.payments_available || current || paying !== null}
                  >
                    {current
                      ? "Подключено"
                      : paying === plan.code
                        ? "Создаём счёт…"
                        : !state.payments_available
                          ? "Оплата недоступна"
                          : purchaseMode === "telegram"
                            ? "Оплатить в Telegram"
                            : purchaseMode === "stars"
                              ? `Оплатить ${plan.stars_amount ?? ""} ★`
                              : state.payments_demo
                                ? "Демо-оплата"
                                : "Перейти к оплате"}
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
            Подписка не продлевается автоматически: новые платежи не списываются без вашей оплаты.
            Отменить подписку можно в этом разделе — доступ сохранится до конца оплаченного периода.
          </p>
          <p>
            {starsProvider
              ? "Оплата проходит внутри Telegram через Stars. Zooffer не получает данные карты и не хранит платёжные реквизиты. Возврат Stars оформляется через поддержку."
              : "Платёжные данные вводятся только на стороне платёжного провайдера. Zooffer не хранит номера карт. Чеки и возвраты регулируются офертой и законодательством РФ."}
          </p>
          <Link href={legalPath} className="text-link">
            Условия подписки и возврата
          </Link>
        </div>
      </section>
    </>
  );
}
