import type { Metadata } from "next";
import Link from "next/link";

import { CategoryGrid } from "@/components/category-grid";
import { FeaturedStack } from "@/components/featured-stack";
import { ArrowIcon, CheckIcon, PawIcon, ShieldIcon, SparkIcon } from "@/components/icons";
import { ListingCard } from "@/components/listing-card";
import { Reveal } from "@/components/reveal";
import { getHome } from "@/lib/data";

export const metadata: Metadata = {
  title: "Zooffer — животные находят своих людей",
  description:
    "Подбор животных для дома, вязки и племенного разведения. Живые объявления, взаимные совпадения и безопасная переписка внутри Zooffer.",
  alternates: { canonical: "/" },
};

const steps = [
  {
    title: "Создайте анкету",
    text: "Расскажите о животном, добавьте фотографии и укажите, кого ищете.",
  },
  {
    title: "Листайте подбор",
    text: "Смотрите карточки, сохраняйте понравившихся и пропускайте остальных без давления.",
  },
  {
    title: "Совпадение или запрос",
    text: "При взаимной симпатии откроется чат. К объявлению можно написать напрямую.",
  },
  {
    title: "Договаривайтесь безопасно",
    text: "Общайтесь внутри платформы, проверяйте документы и не отправляйте предоплату вслепую.",
  },
];

export default async function HomePage() {
  const home = await getHome();
  const featured = home?.featured?.length ? home.featured : (home?.recent ?? []);
  const categories = home?.categories ?? [];
  const total = categories.reduce((sum, item) => sum + item.count, 0);
  const cards = featured.slice(0, 8);
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Zooffer",
    url: process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000",
    potentialAction: {
      "@type": "SearchAction",
      target: `${process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000"}/search?q={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <span className="eyebrow">Zooffer · забота в каждом знакомстве</span>
            <h1 className="display hero-title">
              <span className="line">
                <span>Найдите</span>
              </span>
              <span className="line">
                <span>
                  <em>того самого</em>
                </span>
              </span>
              <span className="line">
                <span>для себя или питомца</span>
              </span>
            </h1>
            <p className="lead">
              Продажа, вязка, племенное разведение и пристройство — в одном спокойном пространстве.
              Без бесконечных звонков и случайных сообщений: только взаимный интерес.
            </p>
            <div className="btn-row">
              <Link href="/discovery" className="btn btn-primary">
                Начать подбор <ArrowIcon />
              </Link>
              <Link href="/account/listings/new" className="btn btn-secondary">
                Разместить объявление
              </Link>
            </div>
            <div className="hero-stats">
              <span>
                <strong>{total > 0 ? total.toLocaleString("ru-RU") : "24/7"}</strong>
                {total > 0 ? "объявлений в подборе" : "подбор без выходных"}
              </span>
              <span>
                <strong>Только взаимно</strong>
                совпадения и контакты
              </span>
              <span>
                <strong>Безопасно</strong>
                переписка внутри платформы
              </span>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-visual-note">
              <span className="chip chip-brand">
                <SparkIcon width={13} height={13} /> Живая витрина
              </span>
              <p>Карточки можно листать — как в приложении.</p>
            </div>
            <FeaturedStack items={featured.slice(0, 6)} />
          </div>
        </div>
      </section>

      <Reveal>
        <section className="section container" id="categories">
          <div className="section-head">
            <div>
              <span className="eyebrow">Выберите сценарий</span>
              <h2>Не просто объявления</h2>
            </div>
            <p>
              У каждого животного своя история. Мы разделили сценарии, чтобы вы быстрее находили
              нужное — и не тратили время на лишнее.
            </p>
          </div>
          <CategoryGrid categories={categories} />
        </section>
      </Reveal>

      <Reveal>
        <section className="section container" id="featured">
          <div className="section-head">
            <div>
              <span className="eyebrow">Выбор редакции</span>
              <h2>Те, кого уже заметили</h2>
            </div>
            <Link href="/search?sort=newest" className="btn btn-secondary btn-sm">
              Все объявления <ArrowIcon width={16} height={16} />
            </Link>
          </div>
          {cards.length > 0 ? (
            <div className="editorial-grid">
              {cards.map((listing, index) => (
                <div
                  key={listing.public_id}
                  className={index === 0 ? "editorial-lead" : index === 3 ? "editorial-narrow" : ""}
                >
                  <ListingCard listing={listing} priority={index < 2} />
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <PawIcon width={42} height={42} />
              <h2>Первые истории появятся здесь</h2>
              <p>
                Сейчас витрина пуста. Если вы владелец животного или питомник, самое время
                рассказать о нём.
              </p>
              <Link href="/account/listings/new" className="btn btn-primary">
                Создать объявление
              </Link>
            </div>
          )}
        </section>
      </Reveal>

      <Reveal>
        <section className="section section-tinted">
          <div className="container">
            <div className="section-head">
              <div>
                <span className="eyebrow">Как это работает</span>
                <h2>Четыре шага к хорошему знакомству</h2>
              </div>
              <p>
                Zooffer не подменяет ваше решение. Он помогает увидеть больше, услышать друг друга и
                договориться о главном.
              </p>
            </div>
            <div className="steps">
              {steps.map((step) => (
                <div className="step" key={step.title}>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              ))}
            </div>
            <div className="safety-note">
              <ShieldIcon width={22} height={22} />
              <div>
                <strong>Проверяйте перед встречей.</strong> Сверяйте документы, состояние здоровья и
                условия содержания. Не переводите предоплату незнакомым людям и не отправляйте коды
                из SMS. Если что-то настораживает — сообщите в поддержку.
              </div>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="section container">
          <div className="trust-band">
            <div className="trust-copy">
              <span className="eyebrow">Приватность по умолчанию</span>
              <h2>Видно только то, что важно для выбора</h2>
              <p>
                Другие пользователи видят имя владельца и информацию об объявлении. Контакты, почта,
                Telegram и точный адрес остаются скрытыми. Переписка начинается внутри Zooffer.
              </p>
              <ul className="check-list">
                <li>
                  <CheckIcon width={16} height={16} /> Без публичных телефонов и ссылок на соцсети
                </li>
                <li>
                  <CheckIcon width={16} height={16} /> Без онлайн-статусов и «последнего визита»
                </li>
                <li>
                  <CheckIcon width={16} height={16} /> Город указывается без точного адреса
                </li>
              </ul>
            </div>
            <div className="trust-visual" aria-hidden="true">
              <span className="trust-orbit trust-orbit-one" />
              <span className="trust-orbit trust-orbit-two" />
              <span className="trust-shield">
                <ShieldIcon width={48} height={48} />
              </span>
              <span className="trust-label">Только имя</span>
              <span className="trust-label trust-label-two">Без контактов</span>
            </div>
          </div>
        </section>
      </Reveal>

      <Reveal>
        <section className="container cta-section">
          <div className="cta-band">
            <span className="eyebrow eyebrow-light">Начните с одного шага</span>
            <h2>Хорошие встречи начинаются с внимания</h2>
            <p>
              Создайте профиль, добавьте животное или просто посмотрите, кто ищет дом и пару прямо
              сейчас. Это бесплатно.
            </p>
            <div className="btn-row">
              <Link href="/discovery" className="btn btn-primary">
                Перейти к подбору <ArrowIcon />
              </Link>
              <Link href="/register" className="btn btn-secondary">
                Создать аккаунт
              </Link>
            </div>
          </div>
        </section>
      </Reveal>
    </>
  );
}
