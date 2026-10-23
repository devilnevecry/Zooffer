"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ArrowIcon, CloseIcon, EyeIcon, PlusIcon } from "./icons";
import { StatusChip } from "./status-chip";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime, formatListingPrice } from "@/lib/format";
import type { OwnerListing } from "@/lib/types";

type Action = "publish" | "pause" | "renew" | "archive" | "sold";

const labels: Record<Action, string> = {
  publish: "Опубликовать",
  pause: "Снять с публикации",
  renew: "Продлить",
  archive: "В архив",
  sold: "Пометить проданным",
};

export function ListingManager({
  initial,
  basePath = "/account",
  listingPath = "/listing",
}: {
  initial: OwnerListing[];
  basePath?: string;
  listingPath?: string;
}) {
  const router = useRouter();
  const showToast = useToast();
  const [listings, setListings] = useState(initial);
  const [busyId, setBusyId] = useState<string | null>(null);

  const act = async (listing: OwnerListing, action: Action) => {
    if (action === "archive" && !window.confirm("Убрать объявление в архив?")) return;
    if (action === "sold" && !window.confirm("Пометить объявление как проданное?")) return;
    setBusyId(listing.public_id);
    try {
      const updated = await api<OwnerListing>(`/api/v1/listings/${listing.public_id}/${action}`, {
        method: "POST",
      });
      setListings((items) =>
        items.map((item) => (item.public_id === updated.public_id ? updated : item)),
      );
      showToast(labels[action]);
      router.refresh();
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось обновить объявление", "error");
    } finally {
      setBusyId(null);
    }
  };

  if (!listings.length) {
    return (
      <div className="empty-state">
        <h2>Здесь появятся ваши объявления</h2>
        <p>
          Создайте анкету животного и расскажите, кого вы ищете. Черновик можно
          сохранить и вернуться к нему позже.
        </p>
        <Link href={`${basePath}/listings/new`} className="btn btn-primary">
          <PlusIcon /> Создать объявление
        </Link>
      </div>
    );
  }

  return (
    <div className="listing-manager">
      {listings.map((listing) => {
        const busy = busyId === listing.public_id;
        return (
          <article className="manage-card" key={listing.public_id}>
            <div className="manage-main">
              <div className="manage-top">
                <StatusChip status={listing.status} />
                <span className="muted small">
                  Обновлено {formatDateTime(listing.updated_at)}
                </span>
              </div>
              <h2>{listing.title}</h2>
              <p className="manage-description">
                {listing.description
                  ? `${listing.description.slice(0, 160)}${listing.description.length > 160 ? "…" : ""}`
                  : "Описание пока не заполнено."}
              </p>
              <div className="manage-meta">
                <strong>
                  {formatListingPrice(listing.purpose, listing.price_kopecks, listing.negotiable)}
                </strong>
                {listing.published_at && <span>Опубликовано {formatDateTime(listing.published_at)}</span>}
                {listing.expires_at && <span>До {formatDateTime(listing.expires_at)}</span>}
              </div>
              {listing.moderation_reason && (
                <div className="notice warn">
                  <strong>Проверка:</strong> {listing.moderation_reason}
                </div>
              )}
            </div>
            <div className="manage-actions">
              {listing.status === "published" && (
                <>
                  <Link
                    href={`${listingPath}/${listing.slug}`}
                    className="btn btn-secondary btn-sm"
                  >
                    <EyeIcon width={16} height={16} /> Смотреть
                  </Link>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void act(listing, "pause")}
                    disabled={busy}
                  >
                    Снять
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void act(listing, "sold")}
                    disabled={busy}
                  >
                    Продан
                  </button>
                </>
              )}
              {(listing.status === "draft" || listing.status === "rejected" || listing.status === "pending_moderation") && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => void act(listing, "publish")}
                  disabled={busy}
                >
                  {listing.status === "pending_moderation" ? "Отправить снова" : "Опубликовать"}
                </button>
              )}
              {(listing.status === "paused" || listing.status === "expired") && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => void act(listing, "renew")}
                  disabled={busy}
                >
                  Продлить
                </button>
              )}
              <Link
                href={`${basePath}/listings/${listing.public_id}/edit`}
                className="btn btn-ghost btn-sm"
              >
                Редактировать <ArrowIcon width={15} height={15} />
              </Link>
              {listing.status !== "archived" && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm manage-archive"
                  onClick={() => void act(listing, "archive")}
                  disabled={busy}
                  aria-label="Убрать в архив"
                >
                  <CloseIcon width={15} height={15} />
                </button>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}
