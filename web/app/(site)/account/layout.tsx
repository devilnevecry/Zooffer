import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { AccountNav } from "@/components/account-nav";
import { LogoutButton } from "@/components/logout-button";
import { PlusIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";
import { initials } from "@/lib/format";

export const metadata: Metadata = {
  title: "Аккаунт",
  robots: { index: false, follow: false },
};

export default async function AccountLayout({ children }: { children: ReactNode }) {
  const me = await requireMe();
  const user = me.user;

  return (
    <div className="page account-page">
      <div className="container account-grid">
        <aside className="account-sidebar">
          <div className="account-user">
            <span className="avatar avatar-lg">{initials(user.first_name)}</span>
            <div>
              <strong>{user.first_name ?? "Аккаунт Zooffer"}</strong>
              <span>{user.email ?? "Telegram-аккаунт"}</span>
            </div>
          </div>
          <Link href="/account/listings/new" className="btn btn-primary btn-sm account-create">
            <PlusIcon /> Новое объявление
          </Link>
          <AccountNav />
          {["moderator", "admin", "superadmin"].includes(user.role) && (
            <Link href="/admin" className="btn btn-secondary btn-sm">
              Панель управления
            </Link>
          )}
          <LogoutButton />
        </aside>
        <div className="account-content">{children}</div>
      </div>
    </div>
  );
}
