import type { Metadata } from "next";
import Link from "next/link";

import { SupportForm } from "@/components/support-form";
import { ArrowIcon, ShieldIcon } from "@/components/icons";
import { getMe } from "@/lib/api";

export const metadata: Metadata = {
  title: "Поддержка и FAQ",
  description:
    "Ответы на частые вопросы о Zooffer: подбор, объявления, безопасность, приватность, подписка и удаление данных.",
  alternates: { canonical: "/support" },
};

const faq = [
  {
    question: "Как работает подбор?",
    answer:
      "Вы листаете карточки животных и отмечаете «нравится» или «пропустить». Сервер записывает выбор и расходует дневной лимит. Совпадение появляется только при взаимной симпатии, после этого открывается чат.",
  },
  {
    question: "Почему я не вижу телефон владельца?",
    answer:
      "Контакты, Telegram и точный адрес скрыты технически. Общение начинается внутри Zooffer. Контакты можно передать добровольно в переписке, но платформа не делает это автоматически.",
  },
  {
    question: "Сколько стоит размещение?",
    answer:
      "Базовые объявления, избранное и переписка бесплатны. Платные планы расширяют лимиты и функции. Демонстрационные цены не являются публичной офертой до запуска оплаты.",
  },
  {
    question: "Что делать, если объявление подозрительное?",
    answer:
      "Не переводите предоплату и не отправляйте коды из SMS. Напишите в поддержку, указав публичную ссылку на объявление. Мы проверим его и при необходимости ограничим.",
  },
  {
    question: "Как удалить аккаунт?",
    answer:
      "В разделе «Настройки» можно скачать архив данных и удалить аккаунт. Объявления и анкеты снимаются, контакты удаляются, сеансы завершаются. Действие необратимо.",
  },
  {
    question: "Почему объявление попало на проверку?",
    answer:
      "Автоматическая проверка ищет контакты в тексте, запрещённые формулировки и неполные обязательные данные. Чистые объявления публикуются сразу; спорные уходят модератору.",
  },
];

export default async function SupportPage() {
  const me = await getMe();

  return (
    <div className="page">
      <div className="container">
        <nav className="breadcrumbs" aria-label="Хлебные крошки">
          <Link href="/">Главная</Link>
          <span aria-hidden="true">/</span>
          <span>Поддержка</span>
        </nav>

        <section className="page-hero support-hero">
          <div>
            <span className="eyebrow">Помощь</span>
            <h1>Поддержка и частые вопросы</h1>
            <p className="lead">
              Сначала проверьте ответы ниже — возможно, вопрос уже решён. Если нет, отправьте
              обращение: оно сохранится в вашем аккаунте.
            </p>
          </div>
          <div className="support-links">
            <a href="#faq" className="quick-card">
              <span>
                <strong>FAQ</strong>
                <span>Подбор, объявления, оплата</span>
              </span>
              <ArrowIcon width={18} height={18} />
            </a>
            <a href="#safety" className="quick-card">
              <ShieldIcon width={22} height={22} />
              <span>
                <strong>Безопасность</strong>
                <span>Как не стать жертвой мошенников</span>
              </span>
              <ArrowIcon width={18} height={18} />
            </a>
            <a href="#support-form" className="quick-card">
              <span>
                <strong>Написать нам</strong>
                <span>Ответ в аккаунте</span>
              </span>
              <ArrowIcon width={18} height={18} />
            </a>
          </div>
        </section>

        <section className="section" id="faq">
          <div className="section-head">
            <div>
              <span className="eyebrow">FAQ</span>
              <h2>Частые вопросы</h2>
            </div>
          </div>
          <div className="faq-list">
            {faq.map((item) => (
              <details className="faq-item" key={item.question}>
                <summary>{item.question}</summary>
                <p>{item.answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="section safety-block" id="safety">
          <ShieldIcon width={26} height={26} />
          <div>
            <span className="eyebrow">Безопасность</span>
            <h2>Как безопасно договориться</h2>
            <ul className="check-list">
              <li>Встречайтесь в людном месте и не переводите предоплату заранее.</li>
              <li>
                Проверяйте документы животного и состояние здоровья у ветеринара, если это важно.
              </li>
              <li>
                Не отправляйте коды из SMS, пароли и полные данные карты даже «сотруднику
                поддержки».
              </li>
              <li>Обсуждайте условия передачи в переписке Zooffer — так остаётся история.</li>
            </ul>
            <p className="muted">
              Zooffer не является стороной сделки и не гарантирует породу, происхождение или
              здоровье животного. Решение принимайте после личной встречи.
            </p>
          </div>
        </section>

        <section className="section" id="support-form">
          <div className="section-head">
            <div>
              <span className="eyebrow">Обращение</span>
              <h2>Написать в поддержку</h2>
              <p>
                Опишите ситуацию подробно, но без лишних персональных данных. Мы ответим в аккаунте.
              </p>
            </div>
          </div>
          <SupportForm authenticated={Boolean(me)} />
        </section>
      </div>
    </div>
  );
}
