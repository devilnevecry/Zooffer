import Link from "next/link";

import { formatAge, formatListingPrice, purposeLabel, sexLabel } from "@/lib/format";
import type { ListingCard as ListingCardType } from "@/lib/types";

import { PawIcon, PinIcon, ShieldIcon } from "./icons";

export function ListingCard({
  listing,
  priority = false,
  compact = false,
  basePath = "/listing",
}: {
  listing: ListingCardType;
  priority?: boolean;
  compact?: boolean;
  basePath?: string;
}) {
  return (
    <Link href={`${basePath}/${listing.slug}`} className="listing-card">
      <div className={`listing-media${compact ? " listing-media-compact" : ""}`}>
        {listing.primary_photo ? (
          // The API returns already-processed WebP renditions. A plain img keeps the
          // web app independent from the image optimizer during local development.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={listing.primary_photo.url}
            alt={listing.primary_photo.alt ?? `${listing.animal_name} — ${listing.title}`}
            width={listing.primary_photo.width}
            height={listing.primary_photo.height}
            loading={priority ? "eager" : "lazy"}
            fetchPriority={priority ? "high" : "auto"}
          />
        ) : (
          <div className="media-placeholder" aria-hidden="true">
            <PawIcon width={46} height={46} />
            <span>Фото скоро появится</span>
          </div>
        )}
        <span className="chip">{purposeLabel(listing.purpose)}</span>
        {listing.is_featured && (
          <span className="chip chip-accent featured-flag">Выбор Zooffer</span>
        )}
      </div>
      <div className="listing-body">
        <div className="listing-meta">
          <span>{sexLabel(listing.sex)}</span>
          {listing.age_years !== null && (
            <>
              <span aria-hidden="true">·</span>
              <span>{formatAge(listing.age_years)}</span>
            </>
          )}
        </div>
        <h3 className="listing-title">
          {listing.animal_name}
          {listing.breed ? `, ${listing.breed}` : ""}
        </h3>
        <p className="listing-subtitle">{listing.title}</p>
        <div className="listing-footer">
          <span className="listing-price">
            {formatListingPrice(listing.purpose, listing.price_kopecks, listing.negotiable)}
          </span>
          {listing.city && (
            <span className="listing-city">
              <PinIcon width={14} height={14} />
              {listing.city.name}
            </span>
          )}
        </div>
        {(listing.has_pedigree || listing.has_pedigree_document) && (
          <div className="badge-row">
            {listing.has_pedigree && (
              <span className="chip chip-brand">
                <ShieldIcon width={13} height={13} /> Родословная
              </span>
            )}
            {listing.has_pedigree_document && (
              <span className="chip chip-live">Документ проверен</span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
