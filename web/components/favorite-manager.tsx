"use client";

import Link from "next/link";
import { useState } from "react";

import { HeartIcon, PawIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatListingPrice, speciesLabel } from "@/lib/format";
import type { FavoriteItem } from "@/lib/types";

export function FavoriteManager({
  initial,
  listingPath = "/listing",
  discoveryPath = "/discovery",
}: {
  initial: FavoriteItem[];
  listingPath?: string;
  discoveryPath?: string;
}) {
  const showToast = useToast();
  const [items, setItems] = useState(initial);
  const [busyId, setBusyId] = useState<string | null>(null);

  const remove = async (item: FavoriteItem) => {
    setBusyId(item.public_id);
    try {
      await api(`/api/v1/favorites/${item.public_id}`, { method: "DELETE" });
      setItems((current) => current.filter((entry) => entry.public_id !== item.public_id));
      showToast("Удалено из избранного");
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось обновить", "error");
    } finally {
      setBusyId(null);
    }
  };

  if (!items.length) {
    return (
      <div className="empty-state">
        <HeartIcon width={44} height={44} />
        <h2>В избранном пока пусто</h2>
        <p>
          Сохраняйте понравившихся животных во время подбора или из объявления — они
          останутся здесь.
        </p>
        <Link href={discoveryPath} className="btn btn-primary">
          Начать подбор
        </Link>
      </div>
    );
  }

  return (
    <div className="favorite-list">
      {items.map((item) => (
        <article className="favorite-row" key={item.public_id}>
          <Link href={`${listingPath}/${item.slug}`} className="favorite-media">
            {item.primary_photo_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={item.primary_photo_url} alt={item.animal_name} />
            ) : (
              <PawIcon width={30} height={30} />
            )}
          </Link>
          <div className="grow">
            <span className="chip">{speciesLabel(item.species)}</span>
            <h2>
              <Link href={`${listingPath}/${item.slug}`}>{item.animal_name}</Link>
            </h2>
            <p>{item.title}</p>
            <strong>{formatListingPrice(item.purpose, item.price_kopecks)}</strong>
          </div>
          <div className="manage-actions">
            <Link href={`${listingPath}/${item.slug}`} className="btn btn-secondary btn-sm">
              Открыть
            </Link>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void remove(item)}
              disabled={busyId === item.public_id}
            >
              Убрать
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
