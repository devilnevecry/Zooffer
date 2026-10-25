import type { ReactNode } from "react";

import { PawIcon, ShieldIcon, SparkIcon } from "./icons";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
  eyebrow = "Zooffer",
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
  eyebrow?: string;
}) {
  return (
    <div className="page auth-page">
      <div className="container auth-grid">
        <div className="auth-aside">
          <span className="eyebrow">{eyebrow}</span>
          <h2>Хорошие знакомства начинаются с доверия</h2>
          <p>
            Один аккаунт для сайта и Telegram. Контакты скрыты, совпадения только взаимные, а
            переписка остаётся внутри Zooffer.
          </p>
          <ul className="auth-points">
            <li>
              <ShieldIcon width={18} height={18} /> Только имя и объявление видны другим
            </li>
            <li>
              <SparkIcon width={18} height={18} /> Подбор без случайных сообщений
            </li>
            <li>
              <PawIcon width={18} height={18} /> Один профиль для всех устройств
            </li>
          </ul>
          <div className="auth-art" aria-hidden="true">
            <span className="auth-art-ring" />
            <span className="auth-art-paw">
              <PawIcon width={54} height={54} />
            </span>
            <span className="auth-art-label">zooffer</span>
          </div>
        </div>
        <div className="form-card auth-card">
          <div className="form-head">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          {children}
          {footer && <div className="form-note">{footer}</div>}
        </div>
      </div>
    </div>
  );
}
