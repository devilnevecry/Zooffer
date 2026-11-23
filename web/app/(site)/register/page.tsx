import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth-shell";
import { TelegramAuth } from "@/components/telegram-auth";
import { getMe } from "@/lib/api";

export const metadata: Metadata = {
  title: "Регистрация",
  description: "Создайте аккаунт Zooffer через Telegram: подбор животных, объявления и переписка.",
  robots: { index: false, follow: false },
};

export default async function RegisterPage() {
  const me = await getMe();
  if (me) redirect("/account");

  return (
    <AuthShell
      title="Аккаунт через Telegram"
      subtitle="Подтвердите вход в Telegram — профиль создастся автоматически. Имя видно другим, контакты остаются приватными."
    >
      <Suspense fallback={<div className="loading-line" />}>
        <TelegramAuth intent="register" />
      </Suspense>
    </AuthShell>
  );
}
