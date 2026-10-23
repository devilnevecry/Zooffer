import type { Metadata } from "next";
import { Suspense } from "react";

import { AuthShell } from "@/components/auth-shell";
import { VerifyEmail } from "@/components/verify-email";

export const metadata: Metadata = {
  title: "Подтверждение почты",
  robots: { index: false, follow: false },
};

export default function VerifyEmailPage() {
  return (
    <AuthShell
      title="Подтверждение почты"
      subtitle="Проверяем ссылку и закрепляем адрес за аккаунтом."
    >
      <Suspense fallback={<div className="loading-line" />}>
        <VerifyEmail />
      </Suspense>
    </AuthShell>
  );
}
