import type { Metadata } from "next";
import Link from "next/link";

import { PartnerInquiryForm } from "@/components/partner-inquiry-form";
import { ArrowIcon, CheckIcon, ShieldIcon } from "@/components/icons";
import { getPartnerOffers } from "@/lib/data";

export const metadata: Metadata = {
  title: "Партнёрам",
  description:
    "Сотрудничество с Zooffer: предложения для владельцев животных, честная маркировка рекламы и прозрачная статистика.",
  alternates: { canonical: "/partners" },
};

const categoryLabels: Record<string, string> = {
  food: "Корм",
  stores: "Магазины",
  vet: "Ветеринария",
  grooming: "Груминг",
  services: "Услуги",
};

export default async function PartnersPage() {
  const offers = await getPartnerOffers();
  const items = offers?.items ?? [];

  return (
    <div className="page">
      <div className="container">
        <nav className="breadcrumbs" aria-label="Хлебные крошки">
          <Link href="/">Главная</Link>
          <span aria-hidden="true">/</span>
          <span>Партнёрам</span>
        </nav>

        <section className="page-hero partner-hero">
          <div>
            <span className="eyebrow">Сотрудничество</span>
            <h1>Полезные предложения без навязчивой рекламы</h1>
            <p className="lead">
              Zooffer показывает партнёрские предложения только там, где они помогают владельцам
              животных: корм, ветеринария, груминг и сервисы. Каждый материал маркируется, а
              статистика считается без персональных данных.
            </p>
            <div className="btn-row">
              <a href="#partner-form" className="btn btn-primary">
                Стать партнёром <ArrowIcon />
              </a>
              <a href="#offers" className="btn btn-secondary">
                Смотреть предложения
              </a>
            </div>
          </div>
          <div className="partner-principles">
            <div>
              <CheckIcon width={18} height={18} />
              <span>Только проверенные компании и понятные условия</span>
            </div>
            <div>
              <CheckIcon width={18} height={18} />
              <span>Маркировка рекламы и ERID там, где это требуется</span>
            </div>
            <div>
              <CheckIcon width={18} height={18} />
              <span>Клики считаются обезличенно, без продажи контактов</span>
            </div>
          </div>
        </section>

        <section className="section" id="offers">
          <div className="section-head">
            <div>
              <span className="eyebrow">Предложения</span>
              <h2>Партнёрские предложения</h2>
              <p>Раздел скрыт, пока нет активных партнёрских материалов.</p>
            </div>
          </div>
          {items.length === 0 ? (
            <div className="empty-state">
              <ShieldIcon width={44} height={44} />
              <h2>Пока нет активных предложений</h2>
              <p>
                Мы не публикуем выдуманные скидки и партнёров. Когда появятся проверенные
                предложения, они будут показаны здесь с условиями и маркировкой.
              </p>
              <a href="#partner-form" className="btn btn-primary">
                Предложить сотрудничество
              </a>
            </div>
          ) : (
            <div className="partner-grid">
              {items.map((offer) => (
                <article className="partner-card" key={offer.public_id}>
                  <div className="badge-row">
                    <span className="chip chip-brand">{offer.partner_name}</span>
                    <span className="chip">{categoryLabels[offer.category] ?? offer.category}</span>
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
        </section>

        <section className="section partner-form-section" id="partner-form">
          <div className="section-head">
            <div>
              <span className="eyebrow">Заявка</span>
              <h2>Расскажите о вашем предложении</h2>
              <p>
                Мы рассматриваем заявки вручную: проверяем компанию, условия и пользу для животных.
                Отправка заявки не гарантирует размещение.
              </p>
            </div>
          </div>
          <PartnerInquiryForm />
        </section>
      </div>
    </div>
  );
}
