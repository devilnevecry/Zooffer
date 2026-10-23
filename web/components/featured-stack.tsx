"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { formatAge, formatListingPrice, purposeLabel } from "@/lib/format";
import type { ListingCard } from "@/lib/types";

import { ArrowIcon, CloseIcon, HeartIcon, PawIcon } from "./icons";

type Drag = {
  startX: number;
  startY: number;
  x: number;
  y: number;
  active: boolean;
};

const emptyDrag: Drag = { startX: 0, startY: 0, x: 0, y: 0, active: false };

export function FeaturedStack({ items }: { items: ListingCard[] }) {
  const [index, setIndex] = useState(0);
  const [drag, setDrag] = useState<Drag>(emptyDrag);
  const [leaving, setLeaving] = useState<"like" | "skip" | null>(null);
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timeout.current) clearTimeout(timeout.current);
    },
    [],
  );

  if (!items.length) {
    return (
      <div className="stack-scene stack-empty">
        <div className="empty-state">
          <PawIcon width={40} height={40} />
          <h2>Скоро здесь появятся животные</h2>
          <p>Опубликуйте первое объявление — и оно станет частью витрины Zooffer.</p>
          <Link href="/account/listings/new" className="btn btn-primary">
            Разместить объявление
          </Link>
        </div>
      </div>
    );
  }

  const visible = [0, 1, 2]
    .map((offset) => items[(index + offset) % items.length])
    .filter(Boolean);

  const decide = (direction: "like" | "skip") => {
    if (leaving) return;
    setLeaving(direction);
    if (timeout.current) clearTimeout(timeout.current);
    timeout.current = setTimeout(() => {
      setIndex((current) => (current + 1) % items.length);
      setLeaving(null);
      setDrag(emptyDrag);
    }, 300);
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (leaving) return;
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
    setDrag((current) => ({
      ...current,
      x: event.clientX - current.startX,
      y: event.clientY - current.startY,
    }));
  };

  const onPointerUp = () => {
    if (!drag.active) return;
    const threshold = 68;
    if (drag.x > threshold) {
      decide("like");
    } else if (drag.x < -threshold) {
      decide("skip");
    } else {
      setDrag(emptyDrag);
    }
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "ArrowRight" || event.key === "ArrowUp") {
      event.preventDefault();
      decide("like");
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      decide("skip");
    }
  };

  const dir = leaving ?? (drag.x > 35 ? "like" : drag.x < -35 ? "skip" : undefined);

  return (
    <div className="stack-wrap">
      <div
        className="stack-scene"
        role="group"
        aria-roledescription="карусель"
        aria-label="Избранные животные Zooffer"
        tabIndex={0}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={() => setDrag(emptyDrag)}
      >
        {visible
          .map((listing, position) => ({ listing, position }))
          .reverse()
          .map(({ listing, position }) => {
            const isTop = position === 0;
            const rotate = position === 1 ? -3 : position === 2 ? 4 : 0;
            const translateY = position === 1 ? 12 : position === 2 ? 24 : 0;
            const scale = position === 1 ? 0.965 : position === 2 ? 0.93 : 1;
            const style = isTop
              ? {
                  transform: `translate(${drag.x}px, ${drag.y}px) rotate(${drag.x / 22}deg)`,
                  transition: drag.active
                    ? "none"
                    : leaving
                      ? "transform 300ms cubic-bezier(0.22, 1, 0.36, 1), opacity 220ms ease"
                      : "transform 420ms cubic-bezier(0.22, 1, 0.36, 1)",
                  opacity: leaving ? 0 : 1,
                  zIndex: 3,
                }
              : {
                  transform: `translateY(${translateY}px) rotate(${rotate}deg) scale(${scale})`,
                  transition: "transform 420ms cubic-bezier(0.22, 1, 0.36, 1)",
                  zIndex: 2 - position,
                };
            return (
              <div
                className="stack-card"
                key={`${listing.public_id}-${position}`}
                data-dir={isTop ? dir : undefined}
                data-top={isTop}
                style={style}
              >
                {listing.primary_photo ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={listing.primary_photo.url}
                    alt={listing.primary_photo.alt ?? `${listing.animal_name}, ${listing.breed ?? ""}`}
                    width={listing.primary_photo.width}
                    height={listing.primary_photo.height}
                    draggable={false}
                    loading={position === 0 ? "eager" : "lazy"}
                  />
                ) : (
                  <div className="stack-photo-placeholder">
                    <PawIcon width={64} height={64} />
                  </div>
                )}
                <span className="stack-stamp like">Нравится</span>
                <span className="stack-stamp skip">Дальше</span>
                <div className="stack-overlay">
                  <span className="chip stack-purpose">{purposeLabel(listing.purpose)}</span>
                  <h3>{listing.animal_name}</h3>
                  <p>
                    {[
                      listing.breed,
                      listing.age_years !== null ? formatAge(listing.age_years) : null,
                      listing.city?.name,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <div className="stack-price-row">
                    <strong>
                      {formatListingPrice(listing.purpose, listing.price_kopecks, listing.negotiable)}
                    </strong>
                    {isTop && (
                      <Link
                        href={`/listing/${listing.slug}`}
                        className="stack-link"
                        aria-label={`Открыть объявление: ${listing.title}`}
                      >
                        Смотреть <ArrowIcon width={16} height={16} />
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
      </div>
      <div className="stack-controls">
        <button
          type="button"
          className="round-action skip"
          onClick={() => decide("skip")}
          disabled={Boolean(leaving)}
          aria-label="Показать следующее животное"
        >
          <CloseIcon />
        </button>
        <span className="stack-counter" aria-live="polite">
          {index + 1} / {items.length}
        </span>
        <button
          type="button"
          className="round-action like"
          onClick={() => decide("like")}
          disabled={Boolean(leaving)}
          aria-label="Сохранить в избранное"
        >
          <HeartIcon />
        </button>
      </div>
      <span className="stack-hint">
        <span aria-hidden="true">← →</span> Листайте карточки или используйте стрелки
      </span>
    </div>
  );
}
