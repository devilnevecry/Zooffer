"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "./auth-provider";
import {
  ArrowIcon,
  CloseIcon,
  HeartIcon,
  PawIcon,
  PinIcon,
  ShieldIcon,
  SparkIcon,
  UndoIcon,
} from "./icons";
import { Modal } from "./modal";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import {
  formatAge,
  formatDateTime,
  formatListingPrice,
  purposeLabel,
  sexLabel,
  speciesLabel,
} from "@/lib/format";
import type { DiscoveryFeed, ListingCard, QuotaView, SwipeResponse } from "@/lib/types";

type Direction = "like" | "skip";
type DragState = {
  startX: number;
  startY: number;
  x: number;
  y: number;
  active: boolean;
};

const emptyDrag: DragState = { startX: 0, startY: 0, x: 0, y: 0, active: false };

export function DiscoveryDeck({ initialFeed }: { initialFeed: DiscoveryFeed | null }) {
  const { user } = useAuth();
  const router = useRouter();
  const showToast = useToast();
  const [items, setItems] = useState<ListingCard[]>(initialFeed?.items ?? []);
  const [cursor, setCursor] = useState(initialFeed?.next_cursor ?? null);
  const [hasMore, setHasMore] = useState(initialFeed?.has_more ?? false);
  const [quota, setQuota] = useState<QuotaView | null>(initialFeed?.quota ?? null);
  const [drag, setDrag] = useState<DragState>(emptyDrag);
  const [leaving, setLeaving] = useState<Direction | null>(null);
  const [busy, setBusy] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [match, setMatch] = useState<{ conversationId: string; name: string } | null>(null);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const leavingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const current = items[0] ?? null;
  const next = items[1] ?? null;

  const loadMore = useCallback(async () => {
    if (!user || loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const query = cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
      const feed = await api<DiscoveryFeed>(`/api/v1/discovery/feed?limit=20${query}`);
      setItems((existing) => {
        const seen = new Set(existing.map((item) => item.public_id));
        return [...existing, ...feed.items.filter((item) => !seen.has(item.public_id))];
      });
      setCursor(feed.next_cursor);
      setHasMore(feed.has_more);
      setQuota(feed.quota);
    } catch {
      // Filling the deck is best-effort; the visible card stays usable.
    } finally {
      setLoadingMore(false);
    }
  }, [user, loadingMore, hasMore, cursor]);

  useEffect(() => {
    if (items.length > 2 || !hasMore || !user) return;
    const timer = window.setTimeout(() => {
      void loadMore();
    }, 200);
    return () => window.clearTimeout(timer);
  }, [items.length, hasMore, user, loadMore]);

  useEffect(
    () => () => {
      if (leavingTimer.current) clearTimeout(leavingTimer.current);
    },
    [],
  );

  const finishSwipe = (direction: Direction) => {
    setLeaving(direction);
    if (leavingTimer.current) clearTimeout(leavingTimer.current);
    leavingTimer.current = setTimeout(() => {
      setItems((existing) => existing.slice(1));
      setLeaving(null);
      setDrag(emptyDrag);
    }, 260);
  };

  const swipe = async (direction: Direction) => {
    if (busy || leaving || !current) return;
    if (!user) {
      router.push("/register?next=/discovery");
      return;
    }
    setBusy(true);
    setLeaving(direction);
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
          source: "web",
        },
      });
      setQuota((previous) =>
        previous
          ? {
              ...previous,
              used: result.unlimited ? previous.used : result.limit - result.remaining,
              remaining: result.remaining,
              limit: result.limit,
              unlimited: result.unlimited,
              resets_at: result.resets_at,
            }
          : previous,
      );
      if (result.match_created && result.conversation_public_id) {
        setMatch({
          conversationId: result.conversation_public_id,
          name: current.animal_name,
        });
      }
      setBusy(false);
      finishSwipe(direction);
    } catch (err) {
      setBusy(false);
      setLeaving(null);
      setDrag(emptyDrag);
      if (err instanceof ClientApiError && err.code === "quota_exceeded") {
        showToast("Лимит показов на сегодня закончился", "error");
        try {
          const fresh = await api<QuotaView>("/api/v1/discovery/quota");
          setQuota(fresh);
        } catch {
          // Keep the previous quota display.
        }
      } else {
        showToast(
          err instanceof ClientApiError ? err.message : "Не удалось сохранить выбор",
          "error",
        );
      }
    }
  };

  const toggleFavorite = async () => {
    if (!current) return;
    if (!user) {
      router.push("/login?next=/discovery");
      return;
    }
    const saved = favorites.has(current.public_id);
    try {
      await api(`/api/v1/favorites/${current.public_id}`, {
        method: saved ? "DELETE" : "POST",
      });
      setFavorites((existing) => {
        const nextSet = new Set(existing);
        if (saved) nextSet.delete(current.public_id);
        else nextSet.add(current.public_id);
        return nextSet;
      });
      showToast(saved ? "Удалено из избранного" : "Сохранено в избранное");
    } catch {
      showToast("Не удалось обновить избранное", "error");
    }
  };

  const undo = async () => {
    if (!user) {
      router.push("/login?next=/discovery");
      return;
    }
    try {
      await api("/api/v1/discovery/undo", { method: "POST" });
      showToast("Последнее решение отменено");
      const feed = await api<DiscoveryFeed>("/api/v1/discovery/feed?limit=20");
      setItems(feed.items);
      setCursor(feed.next_cursor);
      setHasMore(feed.has_more);
      setQuota(feed.quota);
      setDrag(emptyDrag);
      setLeaving(null);
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось отменить", "error");
    }
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (busy || leaving) return;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    setDrag({
      startX: event.clientX,
      startY: event.clientY,
      x: 0,
      y: 0,
      active: true,
    });
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!drag.active) return;
    setDrag((state) => ({
      ...state,
      x: event.clientX - state.startX,
      y: event.clientY - state.startY,
    }));
  };

  const onPointerUp = () => {
    if (!drag.active) return;
    const threshold = 82;
    if (drag.x > threshold) {
      void swipe("like");
    } else if (drag.x < -threshold) {
      void swipe("skip");
    } else {
      setDrag(emptyDrag);
    }
  };

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (event.key === "ArrowRight" || event.key === "ArrowUp") {
        event.preventDefault();
        void swipe("like");
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        void swipe("skip");
      } else if (event.key.toLowerCase() === "z") {
        event.preventDefault();
        void undo();
      } else if (event.key.toLowerCase() === "f") {
        event.preventDefault();
        void toggleFavorite();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const direction = leaving ?? (drag.x > 42 ? "like" : drag.x < -42 ? "skip" : null);
  const quotaPercent =
    quota && quota.limit > 0 ? Math.max(0, Math.min(100, (quota.remaining / quota.limit) * 100)) : 0;

  return (
    <div className="discovery-page">
      <div className="container">
        <div className="discovery-top">
          <div>
            <span className="eyebrow">Подбор</span>
            <h1>Кто-то уже ждёт знакомства</h1>
          </div>
          <div className="discovery-filters">
            <Link href="/search" className="btn btn-secondary btn-sm">
              Настроить фильтры <ArrowIcon width={16} height={16} />
            </Link>
          </div>
        </div>

        {!user && (
          <div className="guest-banner">
            <div>
              <strong>Это гостевой просмотр.</strong> Чтобы сохранять выбор и
              переписываться, создайте аккаунт.
            </div>
            <div className="btn-row">
              <Link href="/register?next=/discovery" className="btn btn-primary btn-sm">
                Создать аккаунт
              </Link>
              <Link href="/login?next=/discovery" className="btn btn-secondary btn-sm">
                Войти
              </Link>
            </div>
          </div>
        )}

        <div className="discovery-layout">
          <div className="deck-column">
            {quota && !quota.unlimited && (
              <div className="deck-quota">
                <span>
                  <strong>{quota.remaining}</strong> из {quota.limit} показов осталось
                </span>
                <div className="quota-bar" aria-hidden="true">
                  <span style={{ width: `${quotaPercent}%` }} />
                </div>
                <span className="quota-reset">
                  до {formatDateTime(quota.resets_at).split(",").slice(-1)}
                </span>
              </div>
            )}
            {quota?.unlimited && (
              <div className="deck-quota">
                <span>
                  <SparkIcon width={16} height={16} /> Безлимитный подбор активен
                </span>
              </div>
            )}

            {current ? (
              <>
                <div className="deck" aria-live="polite">
                  {next && (
                    <div className="deck-card deck-card-next" aria-hidden="true">
                      {next.primary_photo ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={next.primary_photo.url} alt="" />
                      ) : (
                        <div className="deck-photo-placeholder">
                          <PawIcon />
                        </div>
                      )}
                    </div>
                  )}
                  <div
                    className="deck-card"
                    key={current.public_id}
                    data-dir={direction}
                    style={{
                      transform: `translate(${drag.x}px, ${drag.y}px) rotate(${drag.x / 26}deg)`,
                      transition: drag.active
                        ? "none"
                        : leaving
                          ? "transform 260ms cubic-bezier(0.22, 1, 0.36, 1), opacity 220ms ease"
                          : "transform 420ms cubic-bezier(0.22, 1, 0.36, 1)",
                      opacity: leaving ? 0 : 1,
                      cursor: drag.active ? "grabbing" : "grab",
                    }}
                    onPointerDown={onPointerDown}
                    onPointerMove={onPointerMove}
                    onPointerUp={onPointerUp}
                    onPointerCancel={() => setDrag(emptyDrag)}
                  >
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
                      <div className="deck-photo-placeholder">
                        <PawIcon width={64} height={64} />
                        <span>Хозяин скоро добавит фото</span>
                      </div>
                    )}
                    <span className="stack-stamp like">Нравится</span>
                    <span className="stack-stamp skip">Дальше</span>
                    <div className="deck-info">
                      <div className="deck-info-top">
                        <span className="chip chip-brand">{purposeLabel(current.purpose)}</span>
                        <span className="deck-age">
                          {sexLabel(current.sex)}
                          {current.age_years !== null ? ` · ${formatAge(current.age_years)}` : ""}
                        </span>
                      </div>
                      <h2>
                        {current.animal_name}
                        {current.breed ? `, ${current.breed}` : ""}
                      </h2>
                      <p className="deck-title">{current.title}</p>
                      <div className="deck-meta">
                        <span className="listing-price">
                          {formatListingPrice(
                            current.purpose,
                            current.price_kopecks,
                            current.negotiable,
                          )}
                        </span>
                        {current.city && (
                          <span>
                            <PinIcon width={14} height={14} /> {current.city.name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="action-dock" aria-label="Действия с карточкой">
                  <button
                    type="button"
                    className="round-action undo"
                    onClick={() => void undo()}
                    aria-label="Отменить последнее действие (Z)"
                    title="Отменить последнее действие (Z)"
                  >
                    <UndoIcon />
                  </button>
                  <button
                    type="button"
                    className="round-action skip"
                    onClick={() => void swipe("skip")}
                    disabled={busy || Boolean(leaving)}
                    aria-label="Пропустить (стрелка влево)"
                    title="Пропустить (←)"
                  >
                    <CloseIcon />
                  </button>
                  <button
                    type="button"
                    className={`round-action favourite${favorites.has(current.public_id) ? " active" : ""}`}
                    onClick={() => void toggleFavorite()}
                    aria-label="Добавить в избранное (F)"
                    aria-pressed={favorites.has(current.public_id)}
                    title="В избранное (F)"
                  >
                    <HeartIcon fill={favorites.has(current.public_id) ? "currentColor" : "none"} />
                  </button>
                  <button
                    type="button"
                    className="round-action like"
                    onClick={() => void swipe("like")}
                    disabled={busy || Boolean(leaving)}
                    aria-label="Нравится (стрелка вправо)"
                    title="Нравится (→)"
                  >
                    <HeartIcon />
                  </button>
                </div>
                <p className="deck-hint">
                  Перетащите карточку, используйте кнопки или клавиши <kbd>←</kbd>{" "}
                  <kbd>→</kbd> · <kbd>F</kbd> — в избранное · <kbd>Z</kbd> — отменить
                </p>
              </>
            ) : (
              <div className="empty-state deck-empty">
                <PawIcon width={44} height={44} />
                <h2>На сегодня всё</h2>
                <p>
                  Вы посмотрели все подходящие объявления. Загляните позже — новые
                  истории появляются каждый день.
                </p>
                <Link href="/search" className="btn btn-secondary">
                  Перейти к поиску
                </Link>
              </div>
            )}
          </div>

          <aside className="detail-panel discovery-aside">
            {current ? (
              <>
                <span className="eyebrow">О животном</span>
                <h3>{current.animal_name}</h3>
                <p className="muted">{current.title}</p>
                <dl className="detail-list">
                  <div>
                    <dt>Вид</dt>
                    <dd>{speciesLabel(current.species)}</dd>
                  </div>
                  <div>
                    <dt>Порода</dt>
                    <dd>{current.breed || "Не указана"}</dd>
                  </div>
                  <div>
                    <dt>Пол</dt>
                    <dd>{sexLabel(current.sex)}</dd>
                  </div>
                  <div>
                    <dt>Возраст</dt>
                    <dd>{current.age_years !== null ? formatAge(current.age_years) : "Не указан"}</dd>
                  </div>
                  <div>
                    <dt>Город</dt>
                    <dd>{current.city?.name ?? "Не указан"}</dd>
                  </div>
                  <div>
                    <dt>Цена</dt>
                    <dd>
                      {formatListingPrice(
                        current.purpose,
                        current.price_kopecks,
                        current.negotiable,
                      )}
                    </dd>
                  </div>
                </dl>
                <div className="aside-owner">
                  <span className="avatar">{current.owner.display_name?.slice(0, 1) ?? "В"}</span>
                  <div>
                    <strong>{current.owner.display_name ?? "Владелец"}</strong>
                    <p>Контакт откроется в переписке</p>
                  </div>
                </div>
                <Link href={`/listing/${current.slug}`} className="btn btn-secondary btn-sm">
                  Открыть объявление
                </Link>
                <div className="privacy-note">
                  <ShieldIcon width={18} height={18} />
                  Мы не показываем телефоны и Telegram. Начните с сообщения внутри
                  Zooffer.
                </div>
              </>
            ) : (
              <div className="aside-placeholder">
                <SparkIcon width={22} height={22} />
                <p>Здесь появятся детали следующего животного.</p>
              </div>
            )}
            {hasMore && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void loadMore()}
                disabled={loadingMore}
              >
                {loadingMore ? "Загружаем…" : "Загрузить ещё"}
              </button>
            )}
          </aside>
        </div>
      </div>

      <Modal
        open={Boolean(match)}
        onClose={() => setMatch(null)}
        title="Это взаимно"
      >
        <p className="modal-lead">
          Вам понравился {match?.name}, и владелец тоже ответил симпатией. Можно
          начинать разговор — контакты остаются внутри платформы.
        </p>
        <div className="btn-row">
          {match && (
            <Link
              href={`/account/chats/${match.conversationId}`}
              className="btn btn-primary"
              onClick={() => setMatch(null)}
            >
              Открыть чат <ArrowIcon />
            </Link>
          )}
          <button type="button" className="btn btn-secondary" onClick={() => setMatch(null)}>
            Продолжить подбор
          </button>
        </div>
      </Modal>
    </div>
  );
}
