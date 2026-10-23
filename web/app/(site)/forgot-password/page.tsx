import type { Metadata } from "next";
import Link from "next/link";

import { AuthShell } from "@/components/auth-shell";
import { ForgotPasswordForm } from "@/components/forgot-password-form";

export const metadata: Metadata = {
  title: "Восстановление пароля",
  robots: { index: false, follow: false },
};

export default function ForgotPasswordPage() {
  return (
    <AuthShell
      title="Восстановление доступа"
      subtitle="Спокойно: доступ можно вернуть по ссылке из письма."
      footer={
        <>
          Вспомнили пароль? <Link href="/login">Войти</Link>
        </>
      }
    >
      <ForgotPasswordForm />
    </AuthShell>
  );
}
