import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { AdminNav } from "@/components/admin/admin-nav";
import { LogoutButton } from "@/components/logout-button";
import { ShieldIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";

export const metadata: Metadata = {
  title: "Панель управления",
  robots: { index: false, follow: false },
};

const STAFF_ROLES = new Set(["moderator", "admin", "superadmin"]);

export default async function AdminLayout({ children }: { children: ReactNode }) {
  const me = await requireMe("/admin");
  if (!STAFF_ROLES.has(me.user.role)) redirect("/account");
  if (!me.user.mfa_enabled) redirect("/account/settings#mfa");

  return (
    <div className="page account-page admin-page">
      <div className="container account-grid">
        <aside className="account-sidebar">
          <div className="account-user">
            <span className="avatar avatar-lg">
              <ShieldIcon width={22} height={22} />
            </span>
            <div>
              <strong>Панель Zooffer</strong>
              <span>{me.user.role}</span>
            </div>
          </div>
          <AdminNav role={me.user.role} />
          <Link href="/account" className="btn btn-ghost btn-sm">
            Вернуться в аккаунт
          </Link>
          <LogoutButton />
        </aside>
        <div className="account-content">{children}</div>
      </div>
    </div>
  );
}
