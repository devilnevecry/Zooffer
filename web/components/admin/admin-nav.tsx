"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/admin", label: "Сводка", exact: true },
  { href: "/admin/moderation", label: "Модерация" },
  { href: "/admin/reports", label: "Жалобы" },
  { href: "/admin/users", label: "Пользователи", minRole: "admin" },
  { href: "/admin/support", label: "Поддержка" },
  { href: "/admin/payments", label: "Платежи", minRole: "admin" },
  { href: "/admin/settings", label: "Настройки" },
  { href: "/admin/audit", label: "Журнал" },
];

const staffRank: Record<string, number> = {
  moderator: 1,
  admin: 2,
  superadmin: 3,
};

export function AdminNav({ role }: { role: string }) {
  const pathname = usePathname();
  const rank = staffRank[role] ?? 0;
  return (
    <nav className="account-nav" aria-label="Панель управления">
      {links
        .filter((link) => !link.minRole || rank >= staffRank[link.minRole])
        .map((link) => {
          const active = link.exact
            ? pathname === link.href
            : pathname === link.href || pathname.startsWith(`${link.href}/`);
          return (
            <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}>
              {link.label}
            </Link>
          );
        })}
    </nav>
  );
}
