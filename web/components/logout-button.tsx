"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { useToast } from "./toast-provider";

export function LogoutButton() {
  const { logout } = useAuth();
  const router = useRouter();
  const showToast = useToast();
  const [busy, setBusy] = useState(false);

  return (
    <button
      type="button"
      className="account-logout"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await logout();
          router.push("/");
          router.refresh();
        } catch {
          showToast("Не удалось завершить сессию", "error");
        } finally {
          setBusy(false);
        }
      }}
    >
      {busy ? "Выходим…" : "Выйти из аккаунта"}
    </button>
  );
}
