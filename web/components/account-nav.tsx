"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/account", label: "Обзор", exact: true },
  { href: "/account/animals", label: "Мои животные" },
  { href: "/account/listings", label: "Объявления" },
  { href: "/account/favorites", label: "Избранное" },
  { href: "/account/matches", label: "Совпадения" },
  { href: "/account/chats", label: "Сообщения" },
  { href: "/account/notifications", label: "Уведомления" },
  { href: "/account/subscription", label: "Подписка" },
  { href: "/account/settings", label: "Настройки" },
];

export function AccountNav() {
  const pathname = usePathname();
  return (
    <nav className="account-nav" aria-label="Аккаунт">
      {links.map((link) => {
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
