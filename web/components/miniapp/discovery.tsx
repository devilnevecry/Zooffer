"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import {
  ArrowIcon,
  CloseIcon,
  HeartIcon,
  PawIcon,
  PinIcon,
  ShieldIcon,
  SparkIcon,
  UndoIcon,
} from "../icons";
import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatAge, formatListingPrice, purposeLabel, sexLabel, speciesLabel } from "@/lib/format";
import type { DiscoveryFeed, ListingCard, QuotaView, SwipeResponse } from "@/lib/types";

import { useMainButton, useSecondaryButton, useTelegram } from "./telegram";
import { MiniEmpty, MiniError, MiniLoading, useMiniApi } from "./ui";

type Direction = "like" | "skip";

const FEED_PATH = "/api/v1/discovery/feed?limit=20";

export function MiniDiscovery() {
  const { data, loading, error, reload } = useMiniApi<DiscoveryFeed>(FEED_PATH);

  if (loading && !data) return <MiniLoading label="Собираем подборку…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;
  if (!data) return <MiniLoading label="Собираем подборку…" />;

  return <DiscoveryDeck initial={data} />;
}

function DiscoveryDeck({ initial }: { initial: DiscoveryFeed }) {
  const showToast = useToast();
  const { haptic, notify } = useTelegram();
  const [items, setItems] = useState<ListingCard[]>(initial.items);
  const [cursor, setCursor] = useState<string | null>(initial.next_cursor);
  const [hasMore, setHasMore] = useState(initial.has_more);
  const [quota, setQuota] = useState<QuotaView>(initial.quota);
  const [busy, setBusy] = useState(false);
  const [leaving, setLeaving] = useState<Direction | null>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [match, setMatch] = useState<{ conversationId: string; name: string } | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);

  const current = items[0] ?? null;

  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const query = cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
      const feed = await api<DiscoveryFeed>(`${FEED_PATH}${query}`);
      setItems((existing) => {
        const seen = new Set(existing.map((item) => item.public_id));
        return [...existing, ...feed.items.filter((item) => !seen.has(item.public_id))];
      });
      setCursor(feed.next_cursor);
      setHasMore(feed.has_more);
      setQuota(feed.quota);
    } catch {
      // Loading more is best-effort; the visible card remains usable.
    } finally {
      setLoadingMore(false);
    }
  }, [cursor, hasMore, loadingMore]);

  const swipe = useCallback(
    async (direction: Direction) => {
      if (!current || busy || leaving) return;
      setBusy(true);
      setLeaving(direction);
      haptic(direction === "like" ? "medium" : "light");
      try {
        const requestId =
          typeof crypto !== "undefined" && "randomUUID" in crypto
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const result = await api<SwipeResponse>("/api/v1/discovery/swipes", {
          method: "POST",
          body: {
            request_id: requestId,
            action: direction,
            listing_public_id: current.public_id,
            source: "miniapp",
          },
        });
        setQuota((previous) => ({
          ...previous,
          used: result.unlimited ? previous.used : result.limit - result.remaining,
          remaining: result.remaining,
          limit: result.limit,
          unlimited: result.unlimited,
          resets_at: result.resets_at,
        }));
        if (result.match_created && result.conversation_public_id) {
          notify("success");
          setMatch({
            conversationId: result.conversation_public_id,
            name: current.animal_name,
          });
        }
        window.setTimeout(() => {
          setItems((existing) => existing.slice(1));
          setLeaving(null);
          setBusy(false);
        }, 220);
      } catch (err) {
        setLeaving(null);
        setBusy(false);
        if (err instanceof ClientApiError && err.code === "quota_exceeded") {
          notify("error");
          showToast("Лимит показов на сегодня закончился", "error");
          try {
            const fresh = await api<QuotaView>("/api/v1/discovery/quota");
            setQuota(fresh);
          } catch {
            // Keep the previous quota display.
          }
        } else {
          notify("error");
          showToast(
            err instanceof ClientApiError ? err.message : "Не удалось сохранить выбор",
            "error",
          );
        }
      }
    },
    [busy, current, haptic, leaving, notify, showToast],
  );

  const favoriteCurrent = useCallback(async () => {
    if (!current) return;
    const saved = favorites.has(current.public_id);
    try {
      await api(`/api/v1/favorites/${current.public_id}`, {
        method: saved ? "DELETE" : "POST",
      });
      haptic("light");
      setFavorites((existing) => {
        const next = new Set(existing);
        if (saved) next.delete(current.public_id);
        else next.add(current.public_id);
        return next;
      });
      showToast(saved ? "Удалено из избранного" : "Сохранено в избранное");
    } catch {
      showToast("Не удалось обновить избранное", "error");
    }
  }, [current, favorites, haptic, showToast]);

  const undo = useCallback(async () => {
    try {
      await api("/api/v1/discovery/undo", { method: "POST" });
      const feed = await api<DiscoveryFeed>(FEED_PATH);
      setItems(feed.items);
      setCursor(feed.next_cursor);
      setHasMore(feed.has_more);
      setQuota(feed.quota);
      haptic("medium");
      showToast("Последнее решение отменено");
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось отменить", "error");
    }
  }, [haptic, showToast]);

  useMainButton({
    text: "Нравится",
    visible: Boolean(current),
    enabled: Boolean(current) && !busy,
    onClick: () => void swipe("like"),
  });
  useSecondaryButton({
    text: "Пропустить",
    visible: Boolean(current),
    enabled: Boolean(current) && !busy,
    onClick: () => void swipe("skip"),
  });

  const quotaPercent =
    quota.limit > 0
      ? Math.max(0, Math.min(100, (quota.remaining / quota.limit) * 100))
      : 0;

  return (
    <div className="tg-discovery">
      <header className="tg-discovery-head">
        <div>
          <span className="eyebrow">Подбор</span>
          <h1>Кто-то ждёт знакомства</h1>
        </div>
        <Link href="/tg/search" className="tg-icon-link" aria-label="Фильтры поиска">
          <ArrowIcon width={18} height={18} />
        </Link>
      </header>

      {!quota.unlimited && (
        <div className="tg-quota">
          <div className="tg-quota-bar">
            <span style={{ width: `${quotaPercent}%` }} />
          </div>
          <span>
            <strong>{quota.remaining}</strong> из {quota.limit} показов сегодня
          </span>
        </div>
      )}
      {quota.unlimited && (
        <div className="tg-quota unlimited">
          <SparkIcon width={15} height={15} />
          <span>Безлимитный подбор</span>
        </div>
      )}

      {current ? (
        <>
          <div className={`tg-deck${leaving ? ` leaving-${leaving}` : ""}`}>
            <div
              className="tg-swipe-card"
              data-dir={leaving}
              onTouchStart={(event) => {
                const touch = event.touches[0];
                const target = event.currentTarget;
                target.dataset.startX = String(touch.clientX);
              }}
              onTouchEnd={(event) => {
                const target = event.currentTarget;
                const start = Number(target.dataset.startX ?? "0");
                const end = event.changedTouches[0]?.clientX ?? start;
                delete target.dataset.startX;
                if (end - start > 70) void swipe("like");
                else if (start - end > 70) void swipe("skip");
              }}
            >
              <Link href={`/tg/listing/${current.slug}`} className="tg-card-media">
                {current.primary_photo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={current.primary_photo.url}
                    alt={current.primary_photo.alt ?? current.animal_name}
                    width={current.primary_photo.width}
                    height={current.primary_photo.height}
                    draggable={false}
                  />
                ) : (
                  <span className="tg-card-placeholder">
                    <PawIcon width={50} height={50} />
                  </span>
                )}
                <span className="tg-card-purpose">{purposeLabel(current.purpose)}</span>
              </Link>
              <div className="tg-card-body">
                <div className="tg-card-title-row">
                  <h2>
                    {current.animal_name}
                    {current.breed ? `, ${current.breed}` : ""}
                  </h2>
                  <p>
                    {speciesLabel(current.species)} · {sexLabel(current.sex)}
                    {current.age_years !== null ? ` · ${formatAge(current.age_years)}` : ""}
                  </p>
                </div>
                <div className="tg-card-price-row">
                  <strong className="tg-price">
                    {formatListingPrice(
                      current.purpose,
                      current.price_kopecks,
                      current.negotiable,
                    )}
                  </strong>
                  {current.city && (
                    <span className="tg-card-city">
                      <PinIcon width={14} height={14} /> {current.city.name}
                    </span>
                  )}
                </div>
                <p className="tg-card-listing">{current.title}</p>
              </div>
            </div>
          </div>

          <div className="tg-actions" aria-label="Действия">
            <button type="button" className="tg-round tg-round-ghost" onClick={() => void undo()}>
              <UndoIcon width={19} height={19} />
              <span>Отменить</span>
            </button>
            <button
              type="button"
              className="tg-round tg-round-skip"
              onClick={() => void swipe("skip")}
              disabled={busy || Boolean(leaving)}
              aria-label="Пропустить"
            >
              <CloseIcon width={24} height={24} />
            </button>
            <button
              type="button"
              className={`tg-round tg-round-favorite${favorites.has(current.public_id) ? " active" : ""}`}
              onClick={() => void favoriteCurrent()}
              aria-label="В избранное"
            >
              <HeartIcon
                width={20}
                height={20}
                fill={favorites.has(current.public_id) ? "currentColor" : "none"}
              />
            </button>
            <button
              type="button"
              className="tg-round tg-round-like"
              onClick={() => void swipe("like")}
              disabled={busy || Boolean(leaving)}
              aria-label="Нравится"
            >
              <HeartIcon width={26} height={26} />
            </button>
          </div>

          <p className="tg-swipe-hint">
            Свайп вправо — нравится, влево — дальше. Полный профиль открывается по фото.
          </p>

          {hasMore && (
            <button
              type="button"
              className="btn btn-ghost btn-sm tg-load-more"
              onClick={() => void loadMore()}
              disabled={loadingMore}
            >
              {loadingMore ? "Загружаем…" : "Загрузить ещё"}
            </button>
          )}
        </>
      ) : (
        <MiniEmpty
          title="На сегодня всё"
          text="Вы посмотрели подходящие объявления. Новые истории появятся позже — или уточните фильтры."
          href="/tg/search"
          action="Перейти к поиску"
        />
      )}

      <div className="tg-privacy">
        <ShieldIcon width={17} height={17} />
        <span>
          Мы показываем только имя владельца. Телефон, e-mail и Telegram остаются
          скрытыми до вашего решения.
        </span>
      </div>

      {match && (
        <div className="tg-overlay" role="dialog" aria-modal="true" aria-label="Взаимное совпадение">
          <div className="tg-sheet">
            <span className="tg-sheet-mark">
              <HeartIcon width={24} height={24} fill="currentColor" />
            </span>
            <h2>Это взаимно</h2>
            <p>
              Вам понравился {match.name}, и владелец ответил симпатией. Можно начинать
              разговор — контакты остаются внутри Zooffer.
            </p>
            <Link
              href={`/tg/chats/${match.conversationId}`}
              className="btn btn-primary btn-sm"
              onClick={() => setMatch(null)}
            >
              Открыть чат
            </Link>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => setMatch(null)}
            >
              Продолжить подбор
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
