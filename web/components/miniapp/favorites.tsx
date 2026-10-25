"use client";

import Link from "next/link";

import { FavoriteManager } from "../favorite-manager";
import { PlusIcon } from "../icons";
import type { FavoriteList } from "@/lib/types";

import { MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

export function MiniFavorites() {
  const { data, loading, error, reload } = useMiniApi<FavoriteList>("/api/v1/favorites");

  if (loading && !data) return <MiniLoading label="Открываем избранное…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;

  const items = data?.items ?? [];

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Избранное"
        title="Сохранённые"
        lead="Животные, к которым хочется вернуться. Список общий для сайта, бота и Mini App."
        action={
          <Link href="/tg" className="tg-icon-link" aria-label="Продолжить подбор">
            <PlusIcon width={18} height={18} />
          </Link>
        }
      />
      <FavoriteManager initial={items} listingPath="/tg/listing" discoveryPath="/tg" />
    </div>
  );
}
