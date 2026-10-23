import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth-shell";
import { RegisterForm } from "@/components/register-form";
import { getMe } from "@/lib/api";
import { getDictionaries } from "@/lib/data";

export const metadata: Metadata = {
  title: "Регистрация",
  description: "Создайте аккаунт Zooffer: подбор животных, объявления и безопасная переписка.",
  robots: { index: false, follow: false },
};

export default async function RegisterPage() {
  const me = await getMe();
  if (me) redirect("/account");
  const dictionaries = await getDictionaries();

  return (
    <AuthShell
      title="Создайте аккаунт"
      subtitle="Это займёт минуту. Имя и фамилия видны другим, все контакты остаются приватными."
      footer={
        <>
          Уже с нами? <Link href="/login">Войти</Link>
        </>
      }
    >
      <Suspense fallback={<div className="loading-line" />}>
        <RegisterForm dictionaries={dictionaries} />
      </Suspense>
    </AuthShell>
  );
}
