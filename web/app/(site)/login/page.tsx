import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth-shell";
import { LoginForm } from "@/components/login-form";
import { getMe } from "@/lib/api";
import { safeNext } from "@/lib/navigation";

export const metadata: Metadata = {
  title: "Вход",
  description: "Войдите в аккаунт Zooffer.",
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
      title="С возвращением"
      subtitle="Войдите, чтобы продолжить подбор, переписку и управление объявлениями."
      footer={
        <>
          Ещё нет аккаунта? <Link href={`/register?next=${encodeURIComponent(next)}`}>Создать</Link>
        </>
      }
    >
      <Suspense fallback={<div className="loading-line" />}>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
