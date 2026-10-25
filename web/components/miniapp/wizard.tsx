"use client";

import { ListingWizard } from "../listing-wizard";
import type { Dictionaries, OwnerAnimal, OwnerListing } from "@/lib/types";

import { MiniError, MiniLoading, useMiniApi } from "./ui";

export function MiniListingWizard({ listingId }: { listingId?: string }) {
  const editing = Boolean(listingId);
  const dictionaries = useMiniApi<Dictionaries>("/api/v1/public/dictionaries");
  const listing = useMiniApi<OwnerListing>(
    listingId ? `/api/v1/listings/${encodeURIComponent(listingId)}` : null,
  );
  const animals = useMiniApi<{ items: OwnerAnimal[] }>(listingId ? "/api/v1/animals" : null);

  const loading = !dictionaries.data || (editing && (!listing.data || !animals.data));
  const error = dictionaries.error || (editing ? listing.error || animals.error : "");

  if (loading && !error) {
    return <MiniLoading label={editing ? "Открываем черновик…" : "Готовим мастер…"} />;
  }
  if (error) {
    return (
      <MiniError
        message={error}
        onRetry={() => {
          void dictionaries.reload();
          void listing.reload();
          void animals.reload();
        }}
      />
    );
  }

  const initialAnimal = editing
    ? (animals.data?.items.find((item) => item.public_id === listing.data?.animal_public_id) ??
      null)
    : null;

  if (editing && (!listing.data || !initialAnimal)) {
    return <MiniError message="Объявление не найдено или было удалено." />;
  }

  return (
    <div className="tg-wizard-page">
      <header className="tg-wizard-head">
        <span className="eyebrow">Мастер размещения</span>
        <h1>{editing ? "Редактирование" : "Новое объявление"}</h1>
        <p>
          {editing
            ? "После правок объявление проходит повторную проверку."
            : "Черновик сохраняется на сервере после каждого шага."}
        </p>
      </header>
      <ListingWizard
        dictionaries={dictionaries.data}
        initialListing={listing.data}
        initialAnimal={initialAnimal}
        listingsPath="/tg/listings"
      />
    </div>
  );
}
