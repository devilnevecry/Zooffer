import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth-shell";
import { TelegramAuth } from "@/components/telegram-auth";
import { getMe } from "@/lib/api";
import { safeNext } from "@/lib/navigation";

export const metadata: Metadata = {
  title: "Вход",
  description: "Войдите в Zooffer через Telegram.",
  robots: { index: false, follow: false },
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const next = safeNext(typeof params.next === "string" ? params.next : null);
  const me = await getMe();
  if (me) redirect(next);

  return (
    <AuthShell
      title="Вход через Telegram"
      subtitle="Один аккаунт для сайта, бота и Mini App. Почта и пароль не нужны."
    >
      <Suspense fallback={<div className="loading-line" />}>
        <TelegramAuth intent="login" />
      </Suspense>
    </AuthShell>
  );
}
