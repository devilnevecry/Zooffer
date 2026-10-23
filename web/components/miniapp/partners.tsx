"use client";

import { PartnerInquiryForm } from "../partner-inquiry-form";
import { ArrowIcon, ShieldIcon } from "../icons";
import type { PartnerOfferList } from "@/lib/types";

import { MiniEmpty, MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

const categoryLabels: Record<string, string> = {
  food: "Корм",
  stores: "Магазины",
  vet: "Ветеринария",
  grooming: "Груминг",
  services: "Услуги",
};

export function MiniPartners() {
  const { data, loading, error, reload } = useMiniApi<PartnerOfferList>(
    "/api/v1/public/partners",
  );

  if (loading && !data) return <MiniLoading label="Загружаем предложения…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;

  const items = data?.items ?? [];

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Сотрудничество"
        title="Партнёрам"
        lead="Полезные предложения для владельцев животных и честная маркировка рекламы."
      />

      {items.length === 0 ? (
        <MiniEmpty
          title="Пока нет активных предложений"
          text="Мы не публикуем выдуманные скидки и партнёров. Проверенные предложения появятся здесь с условиями и маркировкой."
        />
      ) : (
        <div className="partner-grid tg-partner-grid">
          {items.map((offer) => (
            <article className="partner-card" key={offer.public_id}>
              <div className="badge-row">
                <span className="chip chip-brand">{offer.partner_name}</span>
                <span className="chip">
                  {categoryLabels[offer.category] ?? offer.category}
                </span>
                {(offer.ad_label || offer.erid) && (
                  <span className="chip chip-accent">
                    {offer.ad_label ?? "Реклама"}
                    {offer.erid ? ` · ERID ${offer.erid}` : ""}
                  </span>
                )}
              </div>
              <h2>{offer.title}</h2>
              <p>{offer.description}</p>
              <p className="muted small">{offer.terms}</p>
              {offer.discount_code && (
                <p className="promo-code">
                  Промокод: <strong>{offer.discount_code}</strong>
                </p>
              )}
              <a
                href={`/go/${offer.public_id}`}
                className="btn btn-secondary btn-sm"
                target="_blank"
                rel="nofollow sponsored noreferrer noopener"
              >
                Перейти к предложению <ArrowIcon width={15} height={15} />
              </a>
            </article>
          ))}
        </div>
      )}

      <section className="tg-section">
        <div className="tg-section-head">
          <h2>Стать партнёром</h2>
        </div>
        <p className="tg-lead">
          Мы рассматриваем заявки вручную: проверяем компанию, условия и пользу для
          животных. Отправка заявки не гарантирует размещение.
        </p>
        <PartnerInquiryForm />
      </section>

      <div className="tg-privacy">
        <ShieldIcon width={17} height={17} />
        <span>
          Клики считаются обезличенно. Zooffer не продаёт контакты владельцев и не
          передаёт партнёрам данные аккаунта.
        </span>
      </div>
    </div>
  );
}
