import Link from "next/link";

import { Wordmark } from "./wordmark";

export function SiteFooter() {
  const bot = process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME;
  const channel = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL;

  return (
    <footer className="site-footer">
      <div className="container">
        <div className="footer-grid">
          <div className="footer-brand">
            <Wordmark />
            <p>
              Место, где животные находят дом, пару и заботливых людей. Безопасный
              подбор, живые объявления и переписка внутри платформы.
            </p>
          </div>
          <div className="footer-col">
            <h4>Платформа</h4>
            <Link href="/discovery">Подбор</Link>
            <Link href="/search">Поиск объявлений</Link>
            <Link href="/account/listings/new">Разместить объявление</Link>
            <Link href="/partners">Партнёрам</Link>
          </div>
          <div className="footer-col">
            <h4>Помощь</h4>
            <Link href="/support">Поддержка и FAQ</Link>
            <Link href="/support#safety">Безопасные сделки</Link>
            <Link href="/legal/rules">Правила размещения</Link>
            <Link href="/account/settings">Настройки приватности</Link>
          </div>
          <div className="footer-col">
            <h4>Документы</h4>
            <Link href="/legal/privacy">Политика конфиденциальности</Link>
            <Link href="/legal/terms">Пользовательское соглашение</Link>
            <Link href="/legal/personal-data">Обработка персональных данных</Link>
            <Link href="/legal/requisites">Реквизиты</Link>
          </div>
        </div>
        <div className="footer-bottom">
          <span>© {new Date().getFullYear()} Zooffer. Заботимся о животных и их людях.</span>
          <span className="footer-socials">
            {bot && (
              <a href={`https://t.me/${bot}`} target="_blank" rel="noreferrer noopener">
                Telegram-бот
              </a>
            )}
            {channel && (
              <a href={channel} target="_blank" rel="noreferrer noopener">
                Telegram-канал
              </a>
            )}
            <Link href="/legal/offer">Условия подписки</Link>
          </span>
        </div>
      </div>
    </footer>
  );
}
