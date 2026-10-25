"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useAuth } from "../auth-provider";
import { ChatIcon, HeartIcon, SearchIcon, SparkIcon, UserIcon } from "../icons";
import { api, ClientApiError } from "@/lib/client";
import type { AuthResponse, MeResponse } from "@/lib/types";

interface TelegramButton {
  isVisible: boolean;
  show: () => void;
  hide: () => void;
  enable?: () => void;
  disable?: () => void;
  setText: (text: string) => void;
  setParams?: (params: { color?: string; text_color?: string; is_active?: boolean }) => void;
  showProgress?: (leaveActive?: boolean) => void;
  hideProgress?: () => void;
  onClick: (callback: () => void) => void;
  offClick: (callback: () => void) => void;
}

interface TelegramInset {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: {
    user?: { id?: number; first_name?: string; last_name?: string; username?: string };
  };
  platform?: string;
  colorScheme?: "light" | "dark";
  themeParams?: Record<string, string>;
  viewportHeight?: number;
  viewportStableHeight?: number;
  safeAreaInset?: TelegramInset;
  contentSafeAreaInset?: TelegramInset;
  isExpanded?: boolean;
  ready: () => void;
  expand: () => void;
  close: () => void;
  setHeaderColor?: (color: string) => void;
  setBackgroundColor?: (color: string) => void;
  enableClosingConfirmation?: () => void;
  disableClosingConfirmation?: () => void;
  requestFullscreen?: () => void;
  isVersionAtLeast?: (version: string) => boolean;
  onEvent: (event: string, callback: () => void) => void;
  offEvent: (event: string, callback: () => void) => void;
  BackButton?: TelegramButton;
  MainButton?: TelegramButton;
  SecondaryButton?: TelegramButton;
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
    selectionChanged: () => void;
  };
  openInvoice?: (url: string, callback?: (status: string) => void) => void;
  openTelegramLink?: (url: string) => void;
  shareToStory?: (mediaUrl: string, params?: Record<string, unknown>) => void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

interface TelegramContextValue {
  webApp: TelegramWebApp | null;
  available: boolean;
  platform: string | null;
  haptic: (style?: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
  notify: (type: "error" | "success" | "warning") => void;
  share: (url: string, text: string) => void;
  openTelegramLink: (url: string) => void;
  requestFullscreen: () => void;
  openInvoice: (url: string) => Promise<string>;
  setClosingConfirmation: (enabled: boolean) => void;
}

const TelegramContext = createContext<TelegramContextValue | null>(null);

const BOT_URL = process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL ?? "";

function detectWebApp(): TelegramWebApp | null {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp ?? null;
}

function readCachedName(webApp: TelegramWebApp | null): string {
  if (!webApp?.initDataUnsafe?.user) return "";
  const user = webApp.initDataUnsafe.user;
  return [user.first_name, user.last_name].filter(Boolean).join(" ");
}

export function MiniAppRoot({ children }: { children: ReactNode }) {
  const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);
  const [sdkChecked, setSdkChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const applyInsets = (app: TelegramWebApp) => {
      if (typeof document === "undefined") return;
      const root = document.documentElement;
      const safe = app.safeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };
      const content = app.contentSafeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };
      root.style.setProperty("--tg-safe-top", `${Math.max(safe.top, content.top)}px`);
      root.style.setProperty("--tg-safe-bottom", `${Math.max(safe.bottom, content.bottom)}px`);
      root.style.setProperty("--tg-safe-left", `${Math.max(safe.left, content.left)}px`);
      root.style.setProperty("--tg-safe-right", `${Math.max(safe.right, content.right)}px`);
      if (app.viewportStableHeight) {
        root.style.setProperty("--tg-viewport-height", `${app.viewportStableHeight}px`);
      }
      root.dataset.tgTheme = app.colorScheme === "dark" ? "dark" : "light";
      const params = app.themeParams ?? {};
      if (params.bg_color) root.style.setProperty("--tg-theme-bg", params.bg_color);
      if (params.secondary_bg_color) {
        root.style.setProperty("--tg-theme-secondary-bg", params.secondary_bg_color);
      }
      if (params.text_color) root.style.setProperty("--tg-theme-text", params.text_color);
      if (params.hint_color) root.style.setProperty("--tg-theme-hint", params.hint_color);
      if (params.link_color) root.style.setProperty("--tg-theme-link", params.link_color);
    };

    const boot = (app: TelegramWebApp) => {
      if (cancelled) return;
      setWebApp(app);
      setSdkChecked(true);
      try {
        app.ready();
        app.expand();
        if (app.themeParams?.bg_color) app.setBackgroundColor?.(app.themeParams.bg_color);
        if (app.themeParams?.secondary_bg_color) {
          app.setHeaderColor?.(app.themeParams.secondary_bg_color);
        }
      } catch {
        // The Mini App must keep working when an older client lacks an API.
      }
      applyInsets(app);
      const onViewport = () => applyInsets(app);
      const onTheme = () => {
        applyInsets(app);
        if (app.colorScheme === "dark") app.setHeaderColor?.("#111827");
        else app.setHeaderColor?.("#f3f6fa");
      };
      app.onEvent("viewportChanged", onViewport);
      app.onEvent("themeChanged", onTheme);
    };

    const app = detectWebApp();
    if (app) {
      boot(app);
      return () => {
        cancelled = true;
      };
    }

    // Inside Telegram the SDK script is normally already injected. When it is not,
    // wait for it briefly instead of declaring the visitor "outside Telegram".
    const likelyTelegram =
      /Telegram/i.test(window.navigator.userAgent) || "TelegramWebviewProxy" in window;
    const deadline = Date.now() + (likelyTelegram ? 5_000 : 500);
    let timer = 0;

    const poll = () => {
      if (cancelled) return;
      const late = detectWebApp();
      if (late) {
        timer = 0;
        boot(late);
        return;
      }
      if (Date.now() >= deadline) {
        timer = 0;
        setSdkChecked(true);
        return;
      }
      timer = window.setTimeout(poll, 120);
    };

    timer = window.setTimeout(poll, 80);

    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  const value = useMemo<TelegramContextValue>(() => {
    const app = webApp;
    return {
      webApp: app,
      available: Boolean(app),
      platform: app?.platform ?? null,
      haptic: (style = "light") => {
        try {
          app?.HapticFeedback?.impactOccurred(style);
        } catch {
          // Haptics are optional.
        }
      },
      notify: (type) => {
        try {
          app?.HapticFeedback?.notificationOccurred(type);
        } catch {
          // Haptics are optional.
        }
      },
      share: (url, text) => {
        const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
        if (app?.openTelegramLink) {
          app.openTelegramLink(shareUrl);
          return;
        }
        if (typeof navigator !== "undefined" && navigator.share) {
          void navigator.share({ url, text }).catch(() => undefined);
          return;
        }
        if (typeof navigator !== "undefined" && navigator.clipboard) {
          void navigator.clipboard.writeText(`${text} ${url}`).catch(() => undefined);
        }
      },
      openTelegramLink: (url) => {
        if (app?.openTelegramLink) app.openTelegramLink(url);
        else if (typeof window !== "undefined") window.open(url, "_blank", "noopener");
      },
      requestFullscreen: () => {
        try {
          app?.requestFullscreen?.();
        } catch {
          // Fullscreen is best-effort and unsupported on many clients.
        }
      },
      openInvoice: (url) =>
        new Promise<string>((resolve) => {
          if (!app?.openInvoice) {
            resolve("unsupported");
            return;
          }
          app.openInvoice(url, (status) => resolve(status));
        }),
      setClosingConfirmation: (enabled) => {
        try {
          if (enabled) app?.enableClosingConfirmation?.();
          else app?.disableClosingConfirmation?.();
        } catch {
          // Older clients simply ignore it.
        }
      },
    };
  }, [webApp]);

  return (
    <TelegramContext.Provider value={value}>
      <MiniAppSessionGate sdkChecked={sdkChecked}>{children}</MiniAppSessionGate>
    </TelegramContext.Provider>
  );
}

export function useTelegram(): TelegramContextValue {
  const value = useContext(TelegramContext);
  if (!value) throw new Error("useTelegram must be used inside MiniAppRoot");
  return value;
}

export function useMainButton({
  text,
  onClick,
  visible = true,
  enabled = true,
  progress = false,
}: {
  text: string;
  onClick: () => void;
  visible?: boolean;
  enabled?: boolean;
  progress?: boolean;
}) {
  const { webApp } = useTelegram();

  useEffect(() => {
    const button = webApp?.MainButton;
    if (!button) return;
    const handler = () => onClick();
    button.setText(text);
    button.onClick(handler);
    if (visible) button.show();
    else button.hide();
    if (enabled) button.enable?.();
    else button.disable?.();
    if (progress) button.showProgress?.();
    else button.hideProgress?.();
    return () => {
      button.offClick(handler);
      button.hide();
      button.hideProgress?.();
    };
  }, [webApp, text, visible, enabled, progress, onClick]);
}

export function useSecondaryButton({
  text,
  onClick,
  visible = true,
  enabled = true,
}: {
  text: string;
  onClick: () => void;
  visible?: boolean;
  enabled?: boolean;
}) {
  const { webApp } = useTelegram();

  useEffect(() => {
    const button = webApp?.SecondaryButton;
    if (!button) return;
    const handler = () => onClick();
    button.setText(text);
    button.onClick(handler);
    if (visible) button.show();
    else button.hide();
    if (enabled) button.enable?.();
    else button.disable?.();
    return () => {
      button.offClick(handler);
      button.hide();
    };
  }, [webApp, text, visible, enabled, onClick]);
}

function MiniAppSessionGate({
  sdkChecked,
  children,
}: {
  sdkChecked: boolean;
  children: ReactNode;
}) {
  const { setSession } = useAuth();
  const [status, setStatus] = useState<"loading" | "ready" | "outside" | "error">("loading");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!sdkChecked) return;
    let cancelled = false;
    const run = async () => {
      setStatus("loading");
      setError("");
      const initData = detectWebApp()?.initData ?? "";
      if (initData) {
        try {
          const payload = await api<AuthResponse>("/api/v1/auth/telegram/miniapp", {
            method: "POST",
            body: { init_data: initData },
          });
          if (cancelled) return;
          setSession(payload);
          setStatus("ready");
        } catch (err) {
          if (cancelled) return;
          setError(
            err instanceof ClientApiError
              ? err.message
              : "Не удалось подтвердить вход через Telegram.",
          );
          setStatus("error");
        }
        return;
      }
      try {
        const me = await api<MeResponse>("/api/v1/auth/me");
        if (cancelled) return;
        setSession(me);
        setStatus("ready");
      } catch {
        if (cancelled) return;
        setStatus("outside");
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [sdkChecked, attempt, setSession]);

  if (status === "loading") {
    return (
      <div className="tg-state">
        <div className="tg-state-mark" aria-hidden="true">
          z
        </div>
        <span className="tg-loader" aria-label="Загружаем Zooffer" />
        <p>Открываем Zooffer…</p>
      </div>
    );
  }

  if (status === "outside") {
    return (
      <div className="tg-state">
        <div className="tg-state-mark" aria-hidden="true">
          z
        </div>
        <h1>Zooffer живёт в Telegram</h1>
        <p>
          Mini App открывается из бота Zooffer. Войдите через Telegram, чтобы сохранить единый
          аккаунт, лимиты и переписку с сайтом.
        </p>
        {BOT_URL ? (
          <a href={BOT_URL} className="btn btn-primary" target="_blank" rel="noreferrer">
            Открыть бота Zooffer
          </a>
        ) : (
          <p className="tg-hint">
            Ссылка на бота появится после настройки Telegram-бота. Сайт продолжает работать без
            Telegram.
          </p>
        )}
        <Link href="/" className="btn btn-secondary">
          Перейти на сайт
        </Link>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="tg-state">
        <div className="tg-state-mark" aria-hidden="true">
          !
        </div>
        <h1>Вход не подтвердился</h1>
        <p>{error || "Telegram передал устаревшие или некорректные данные."}</p>
        <button type="button" className="btn btn-primary" onClick={() => setAttempt((n) => n + 1)}>
          Попробовать снова
        </button>
        {BOT_URL && (
          <a href={BOT_URL} className="btn btn-secondary" target="_blank" rel="noreferrer">
            Переоткрыть из бота
          </a>
        )}
      </div>
    );
  }

  return <MiniAppChrome>{children}</MiniAppChrome>;
}

const navigation = [
  { href: "/tg", label: "Подбор", icon: SparkIcon },
  { href: "/tg/search", label: "Поиск", icon: SearchIcon },
  { href: "/tg/favorites", label: "Избранное", icon: HeartIcon },
  { href: "/tg/chats", label: "Чаты", icon: ChatIcon },
  { href: "/tg/profile", label: "Профиль", icon: UserIcon },
];

function MiniAppChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { webApp, requestFullscreen, setClosingConfirmation } = useTelegram();
  const cachedName = readCachedName(webApp);
  const immersive = pathname.startsWith("/tg/chats/") || pathname === "/tg/listings/new";
  const showNav = !immersive && !/^\/tg\/listings\/[^/]+\/edit$/.test(pathname);
  const draft = pathname === "/tg/listings/new" || /^\/tg\/listings\/[^/]+\/edit$/.test(pathname);

  useEffect(() => {
    const button = webApp?.BackButton;
    if (!button) return;
    const handler = () => router.back();
    if (pathname === "/tg") button.hide();
    else {
      button.onClick(handler);
      button.show();
    }
    return () => {
      button.offClick(handler);
      button.hide();
    };
  }, [webApp, pathname, router]);

  useEffect(() => {
    setClosingConfirmation(draft);
    return () => setClosingConfirmation(false);
  }, [draft, setClosingConfirmation]);

  return (
    <div className="tg-app">
      <header className="tg-topbar">
        <Link href="/tg" className="tg-brand" aria-label="Zooffer">
          <span className="tg-brand-mark" aria-hidden="true">
            z
          </span>
          <span>zooffer</span>
          <span className="tg-brand-chip">mini</span>
        </Link>
        <div className="tg-top-actions">
          {cachedName && <span className="tg-hello">{cachedName.split(" ")[0]}</span>}
          {webApp?.requestFullscreen && (
            <button
              type="button"
              className="tg-icon-button"
              onClick={requestFullscreen}
              aria-label="Развернуть на весь экран"
              title="На весь экран"
            >
              ⤢
            </button>
          )}
        </div>
      </header>

      <main className={`tg-main${showNav ? "" : " tg-main-immersive"}`}>{children}</main>

      {showNav && (
        <nav className="tg-nav" aria-label="Навигация Mini App">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "/tg" ? pathname === "/tg" : pathname.startsWith(item.href);
            return (
              <Link key={item.href} href={item.href} aria-current={active ? "page" : undefined}>
                <Icon width={21} height={21} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      )}
    </div>
  );
}
