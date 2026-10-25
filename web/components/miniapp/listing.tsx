"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { InquiryButton } from "../inquiry-button";
import { ListingGallery } from "../listing-gallery";
import { ReportButton } from "../report-button";
import { HeartIcon, PawIcon, PinIcon, ShareIcon, ShieldIcon } from "../icons";
import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import {
  formatAge,
  formatListingPrice,
  purposeLabel,
  sexLabel,
  sizeLabel,
  speciesLabel,
} from "@/lib/format";
import type { FavoriteList, ListingDetail } from "@/lib/types";

import { useTelegram } from "./telegram";
import { MiniError, MiniLoading, MiniRow, useMiniApi } from "./ui";

export function MiniListing() {
  const params = useParams<{ slug: string }>();
  const slug = typeof params.slug === "string" ? params.slug : "";
  const showToast = useToast();
  const { share, haptic } = useTelegram();
  const { data, loading, error, reload } = useMiniApi<ListingDetail>(
    slug ? `/api/v1/public/listings/${encodeURIComponent(slug)}` : null,
  );
  const [saved, setSaved] = useState(false);
  const [favoritesReady, setFavoritesReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api<FavoriteList>("/api/v1/favorites")
      .then((favorites) => {
        if (cancelled || !data) return;
        setSaved(favorites.items.some((item) => item.public_id === data.public_id));
        setFavoritesReady(true);
      })
      .catch(() => {
        if (!cancelled) setFavoritesReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [data]);

  const toggleFavorite = async () => {
    if (!data || !favoritesReady) return;
    try {
      await api(`/api/v1/favorites/${data.public_id}`, {
        method: saved ? "DELETE" : "POST",
      });
      haptic("light");
      setSaved((value) => !value);
      showToast(saved ? "Удалено из избранного" : "Сохранено в избранное");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось обновить избранное",
        "error",
      );
    }
  };

  const shareListing = () => {
    if (!data || typeof window === "undefined") return;
    const url = `${window.location.origin}/listing/${data.slug}`;
    share(url, `${data.animal.name} — ${data.title}`);
  };

  if (loading && !data) return <MiniLoading label="Открываем объявление…" />;
  if (error || !data) {
    return <MiniError message={error || "Объявление не найдено."} onRetry={reload} />;
  }

  const animal = data.animal;

  return (
    <article className="tg-listing">
      <ListingGallery photos={animal.photos} title={data.title} />

      <div className="tg-listing-body">
        <div className="tg-listing-top">
          <div>
            <span className="chip chip-brand">{purposeLabel(data.purpose)}</span>
            <h1>
              {animal.name}
              {animal.breed ? `, ${animal.breed}` : ""}
            </h1>
            <p className="tg-listing-subtitle">{data.title}</p>
          </div>
          <button
            type="button"
            className={`tg-favorite${saved ? " active" : ""}`}
            onClick={() => void toggleFavorite()}
            aria-pressed={saved}
            aria-label="В избранное"
          >
            <HeartIcon width={22} height={22} fill={saved ? "currentColor" : "none"} />
          </button>
        </div>

        <div className="tg-price-row">
          <strong>{formatListingPrice(data.purpose, data.price_kopecks, data.negotiable)}</strong>
          {data.city && (
            <span>
              <PinIcon width={14} height={14} /> {data.city.name}
            </span>
          )}
        </div>

        <div className="tg-facts">
          <MiniRow label="Вид" value={speciesLabel(animal.species)} />
          <MiniRow label="Пол" value={sexLabel(animal.sex)} />
          <MiniRow
            label="Возраст"
            value={animal.age_years !== null ? formatAge(animal.age_years) : "Не указан"}
          />
          <MiniRow label="Размер" value={sizeLabel(animal.size)} />
          {animal.colour && <MiniRow label="Окрас" value={animal.colour} />}
          <MiniRow
            label="Вакцинация"
            value={animal.vaccinated === null ? "Не указана" : animal.vaccinated ? "Есть" : "Нет"}
          />
          {animal.has_pedigree && (
            <MiniRow label="Родословная" value={animal.pedigree_registry ?? "Есть"} />
          )}
        </div>

        {animal.description && (
          <section className="tg-prose">
            <h2>О животном</h2>
            <p>{animal.description}</p>
          </section>
        )}

        <section className="tg-prose">
          <h2>Описание объявления</h2>
          <p>{data.description}</p>
        </section>

        <div className="tg-owner">
          <span className="avatar">{data.owner.display_name?.slice(0, 1) ?? "В"}</span>
          <div>
            <strong>{data.owner.display_name ?? "Владелец"}</strong>
            <p>Контакт откроется в переписке</p>
          </div>
        </div>

        <div className="tg-listing-cta">
          <InquiryButton
            listingId={data.public_id}
            listingTitle={data.title}
            ownerName={data.owner.display_name}
            chatsPath="/tg/chats"
            className="btn btn-primary"
          />
          <div className="btn-row">
            <button type="button" className="btn btn-secondary" onClick={shareListing}>
              <ShareIcon width={17} height={17} /> Поделиться
            </button>
            <ReportButton
              targetType="listing"
              targetId={data.public_id}
              className="btn btn-ghost btn-sm"
            />
          </div>
        </div>

        <div className="tg-privacy">
          <ShieldIcon width={17} height={17} />
          <span>
            Не отправляйте предоплату и коды из SMS. Контакты передавайте только когда сами решите
            это сделать.
          </span>
        </div>

        {!animal.photos.length && (
          <div className="tg-no-photo">
            <PawIcon width={24} height={24} />
            <span>Владелец ещё не добавил фотографии.</span>
          </div>
        )}
      </div>
    </article>
  );
}
