"use client";

import Link from "next/link";

import { PlusIcon } from "../icons";
import { ListingManager } from "../listing-manager";
import type { OwnerListing } from "@/lib/types";

import { MiniError, MiniLoading, MiniPageHead, useMiniApi } from "./ui";

export function MiniListings() {
  const { data, loading, error, reload } = useMiniApi<OwnerListing[]>("/api/v1/listings");

  if (loading && !data) return <MiniLoading label="Загружаем объявления…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;

  return (
    <div className="tg-stack">
      <MiniPageHead
        eyebrow="Объявления"
        title="Мои объявления"
        lead="Публикация, пауза и правки. После изменений объявление проходит повторную проверку."
        action={
          <Link href="/tg/listings/new" className="tg-icon-link" aria-label="Новое объявление">
            <PlusIcon width={18} height={18} />
          </Link>
        }
      />
      <ListingManager
        initial={data ?? []}
        basePath="/tg"
        listingPath="/tg/listing"
      />
    </div>
  );
}
