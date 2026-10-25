"use client";

import { useAuth } from "../auth-provider";
import { ShieldIcon } from "../icons";
import { SupportForm } from "../support-form";

import { MiniPageHead } from "./ui";

export function MiniSupport() {
  const { user } = useAuth();

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Поддержка"
        title="Мы на связи"
        lead="Опишите ситуацию — ответ появится в уведомлениях аккаунта. Для срочных вопросов о безопасности используйте ту же форму."
      />

      <SupportForm authenticated={Boolean(user)} loginPath="/tg" />

      <div className="tg-privacy">
        <ShieldIcon width={17} height={17} />
        <span>
          Мы никогда не просим пароли, коды из SMS или полные данные карты. Для проверки объявления
          достаточно ссылки или публичного ID.
        </span>
      </div>
    </div>
  );
}
