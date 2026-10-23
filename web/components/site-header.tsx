"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "./auth-provider";
import {
  BellIcon,
  ChatIcon,
  HeartIcon,
  PlusIcon,
  SearchIcon,
  UserIcon,
} from "./icons";
import { Wordmark } from "./wordmark";
import { api } from "@/lib/client";
import { initials } from "@/lib/format";
import type { UnreadCount } from "@/lib/types";

const mainLinks = [
  { href: "/discovery", label: "Подбор" },
  { href: "/search", label: "Поиск" },
  { href: "/partners", label: "Партнёрам" },
  { href: "/support", label: "Помощь" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [unread, setUnread] = useState(0);
  const [scrolled, setScrolled] = useState(false);
  const unreadCount = user ? unread : 0;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!user) return;
    const controller = new AbortController();
    const load = async () => {
      try {
        const result = await api<UnreadCount>("/api/v1/notifications/unread-count", {
          signal: controller.signal,
        });
        setUnread(result.unread_count);
      } catch {
        // The badge is non-critical; keep the previous value on transient errors.
      }
    };
    void load();
    const timer = window.setInterval(load, 45_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [user, pathname]);

  return (
    <header className="site-header" data-scrolled={scrolled}>
      <div className="container header-inner">
        <Wordmark />
        <nav className="main-nav" aria-label="Основная навигация">
          {mainLinks.map((link) => {
            const active =
              link.href === "/search"
                ? pathname.startsWith("/search") || pathname.startsWith("/catalog")
                : pathname.startsWith(link.href);
            return (
              <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}>
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="header-actions">
          {user ? (
            <>
              <Link
                href="/account/favorites"
                className="icon-button header-heart"
                aria-label="Избранное"
              >
                <HeartIcon />
              </Link>
              <Link href="/account/chats" className="icon-button" aria-label="Сообщения">
                <ChatIcon />
              </Link>
              <Link
                href="/account/notifications"
                className="icon-button"
                aria-label={
                  unreadCount > 0
                    ? `Уведомления, непрочитанных: ${unreadCount}`
                    : "Уведомления"
                }
              >
                <BellIcon />
                {unreadCount > 0 && (
                  <span className="badge-dot" aria-hidden="true">
                    {unreadCount > 9 ? "9+" : unreadCount}
                  </span>
                )}
              </Link>
              <Link href="/account/listings/new" className="btn btn-primary btn-sm header-add">
                <PlusIcon /> Разместить
              </Link>
              <Link href="/account" className="avatar-link" aria-label="Мой аккаунт">
                <span className="avatar avatar-sm">{initials(user.first_name)}</span>
              </Link>
            </>
          ) : (
            <>
              <Link href="/search" className="icon-button search-mobile" aria-label="Поиск">
                <SearchIcon />
              </Link>
              <Link href="/login" className="btn btn-ghost btn-sm header-login">
                Войти
              </Link>
              <Link href="/discovery" className="btn btn-primary btn-sm">
                Начать подбор
              </Link>
              <Link href="/account" className="icon-button mobile-profile" aria-label="Профиль">
                <UserIcon />
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
