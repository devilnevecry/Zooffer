"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "./auth-provider";
import { ChatIcon, HeartIcon, SearchIcon, SparkIcon, UserIcon } from "./icons";

const items = [
  { href: "/discovery", label: "Подбор", icon: SparkIcon },
  { href: "/search", label: "Поиск", icon: SearchIcon },
  { href: "/account/favorites", label: "Избранное", icon: HeartIcon },
  { href: "/account/chats", label: "Чаты", icon: ChatIcon },
  { href: "/account", label: "Профиль", icon: UserIcon },
];

export function TabBar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <nav className="tab-bar" aria-label="Быстрая навигация">
      {items.map((item) => {
        const Icon = item.icon;
        const active =
          item.href === "/account"
            ? pathname === "/account" || pathname === "/login" || pathname === "/register"
            : pathname.startsWith(item.href);
        const href =
          !user && item.href.startsWith("/account") ? `/login?next=${item.href}` : item.href;
        return (
          <Link key={item.href} href={href} aria-current={active ? "page" : undefined}>
            <Icon />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
