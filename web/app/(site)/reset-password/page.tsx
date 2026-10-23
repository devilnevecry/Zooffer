import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth-shell";
import { ResetPasswordForm } from "@/components/reset-password-form";

export const metadata: Metadata = {
  title: "Новый пароль",
  robots: { index: false, follow: false },
};

export default function ResetPasswordPage() {
  return (
    <AuthShell
      title="Новый пароль"
      subtitle="Придумайте пароль длиной не меньше 10 символов."
      footer={
        <>
          Нужна помощь? <Link href="/support">Написать в поддержку</Link>
        </>
      }
    >
      <Suspense fallback={<div className="loading-line" />}>
        <ResetPasswordForm />
      </Suspense>
    </AuthShell>
  );
}
