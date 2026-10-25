import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { FavoriteButton } from "@/components/favorite-button";
import { InquiryButton } from "@/components/inquiry-button";
import { ListingCard } from "@/components/listing-card";
import { ListingGallery } from "@/components/listing-gallery";
import { ReportButton } from "@/components/report-button";
import { ShareButton } from "@/components/share-button";
import { ArrowIcon, PinIcon, ShieldIcon } from "@/components/icons";
import { getPublicListing, searchListings } from "@/lib/data";
import {
  formatAge,
  formatDate,
  formatListingPrice,
  purposeLabel,
  sexLabel,
  sizeLabel,
  speciesLabel,
} from "@/lib/format";
import type { ListingDetail } from "@/lib/types";

type PageProps = { params: Promise<{ slug: string }> };

function plainDescription(value: string | null | undefined) {
  if (!value) return [];
  return value
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const listing = await getPublicListing(slug);
  if (!listing) return { title: "Объявление не найдено" };
  const photo = listing.animal.photos[0];
  return {
    title: `${listing.animal.name} — ${listing.title}`,
    description:
      listing.description.slice(0, 180) ||
      `${listing.title}. ${listing.animal.name}, ${speciesLabel(listing.animal.species).toLowerCase()}, ${listing.city?.name ?? "Россия"}.`,
    alternates: { canonical: `/listing/${listing.slug}` },
    openGraph: {
      type: "article",
      title: `${listing.animal.name} — ${listing.title}`,
      description: listing.description.slice(0, 200),
      images: photo ? [{ url: photo.url, width: photo.width, height: photo.height }] : undefined,
    },
  };
}

export default async function ListingPage({ params }: PageProps) {
  const { slug } = await params;
  const listing: ListingDetail | null = await getPublicListing(slug);
  if (!listing) notFound();

  const animal = listing.animal;
  const similar = await searchListings({
    species: animal.species,
    limit: 4,
    sort: "newest",
  });
  const related =
    similar?.items.filter((item) => item.public_id !== listing.public_id).slice(0, 3) ?? [];
  const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  const isSale = listing.purpose === "sale";
  const structuredData =
    isSale && listing.price_kopecks !== null
      ? {
          "@context": "https://schema.org",
          "@type": "Product",
          name: `${animal.name} — ${listing.title}`,
          description: listing.description,
          image: animal.photos.map((photo) => photo.url),
          offers: {
            "@type": "Offer",
            price: (listing.price_kopecks / 100).toFixed(2),
            priceCurrency: "RUB",
            availability: "https://schema.org/InStock",
            url: `${appUrl}/listing/${listing.slug}`,
          },
        }
      : null;

  return (
    <div className="page page-tight listing-page">
      {structuredData && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
      )}
      <div className="container">
        <nav className="breadcrumbs" aria-label="Хлебные крошки">
          <Link href="/">Главная</Link>
          <span aria-hidden="true">/</span>
          <Link href={`/catalog/${listing.purpose}`}>{purposeLabel(listing.purpose)}</Link>
          <span aria-hidden="true">/</span>
          <span>{animal.name}</span>
        </nav>

        <div className="detail-layout">
          <div>
            <ListingGallery photos={animal.photos} title={`${animal.name} — ${listing.title}`} />
          </div>

          <aside className="detail-aside">
            <div className="detail-kicker">
              <span className="chip chip-brand">{purposeLabel(listing.purpose)}</span>
              {listing.is_featured && <span className="chip chip-accent">Выбор Zooffer</span>}
              {animal.has_pedigree && <span className="chip chip-live">Родословная</span>}
            </div>
            <h1>{animal.name}</h1>
            <p className="detail-subtitle">{listing.title}</p>
            <div className="price-line">
              {formatListingPrice(listing.purpose, listing.price_kopecks, listing.negotiable)}
              {listing.negotiable && listing.price_kopecks !== null && <small>возможен торг</small>}
            </div>
            <div className="detail-location">
              {listing.city && (
                <span>
                  <PinIcon width={16} height={16} /> {listing.city.name}
                  {listing.region ? `, ${listing.region.name}` : ""}
                </span>
              )}
              {listing.published_at && <span>Опубликовано {formatDate(listing.published_at)}</span>}
            </div>

            <div className="detail-actions">
              <InquiryButton
                listingId={listing.public_id}
                listingTitle={listing.title}
                ownerName={listing.owner.display_name}
              />
              <div className="detail-actions-row">
                <FavoriteButton listingId={listing.public_id} />
                <ShareButton title={`${animal.name} — ${listing.title}`} />
                <ReportButton
                  targetType="listing"
                  targetId={listing.public_id}
                  className="btn btn-ghost btn-sm"
                />
              </div>
            </div>

            <div className="owner-card">
              <span className="avatar" aria-hidden="true">
                {listing.owner.display_name?.slice(0, 1).toUpperCase() ?? "В"}
              </span>
              <div>
                <strong>{listing.owner.display_name ?? "Владелец"}</strong>
                <p>Связь через сообщения Zooffer</p>
              </div>
            </div>

            <div className="privacy-note">
              <ShieldIcon width={18} height={18} />
              <span>
                Телефон, почта и Telegram владельца скрыты. Не отправляйте предоплату до личной
                встречи и проверки документов.
              </span>
            </div>

            <dl className="detail-list compact-facts">
              <div>
                <dt>Вид</dt>
                <dd>{speciesLabel(animal.species)}</dd>
              </div>
              <div>
                <dt>Порода</dt>
                <dd>{animal.breed || "Не указана"}</dd>
              </div>
              <div>
                <dt>Пол</dt>
                <dd>{sexLabel(animal.sex)}</dd>
              </div>
              <div>
                <dt>Возраст</dt>
                <dd>{animal.age_years !== null ? formatAge(animal.age_years) : "Не указан"}</dd>
              </div>
              <div>
                <dt>Окрас</dt>
                <dd>{animal.colour || "Не указан"}</dd>
              </div>
              <div>
                <dt>Размер</dt>
                <dd>{sizeLabel(animal.size)}</dd>
              </div>
              <div>
                <dt>Прививки</dt>
                <dd>
                  {animal.vaccinated === true
                    ? "Есть, по словам владельца"
                    : animal.vaccinated === false
                      ? "Нет"
                      : "Не указано"}
                </dd>
              </div>
              <div>
                <dt>Документы</dt>
                <dd>
                  {animal.has_pedigree_document ? "Загружены, видны модератору" : "Не загружены"}
                </dd>
              </div>
            </dl>
          </aside>
        </div>

        <div className="detail-content">
          <section className="detail-section">
            <span className="eyebrow">История</span>
            <h2>О животном</h2>
            {plainDescription(animal.description).map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            {!animal.description && <p className="muted">Владелец пока не добавил описание.</p>}
          </section>

          <section className="detail-section">
            <span className="eyebrow">Условия</span>
            <h2>Что важно знать</h2>
            {plainDescription(listing.description).map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
            {!listing.description && (
              <p className="muted">
                Уточните у владельца условия передачи, документы и состояние здоровья.
              </p>
            )}
            {animal.health_notes && (
              <div className="notice">
                <strong>Здоровье:</strong> {animal.health_notes}
              </div>
            )}
            {animal.has_pedigree && (
              <div className="notice">
                <strong>Родословная:</strong> {animal.pedigree_registry ?? "реестр не указан"}
                {animal.has_pedigree_document
                  ? ". Документ загружен и доступен модерации."
                  : ". Документ не загружен."}
              </div>
            )}
          </section>

          <section className="detail-section safety-block">
            <ShieldIcon width={24} height={24} />
            <div>
              <h3>Как безопасно договориться</h3>
              <p>
                Встречайтесь в людном месте, проверяйте документы и состояние животного. Не
                переводите деньги до личной встречи. Если объявление кажется подозрительным,
                напишите в поддержку.
              </p>
              <Link href="/support#safety" className="text-link">
                Правила безопасной сделки <ArrowIcon width={15} height={15} />
              </Link>
            </div>
          </section>
        </div>

        {related.length > 0 && (
          <section className="section related-section">
            <div className="section-head">
              <div>
                <span className="eyebrow">Рядом</span>
                <h2>Похожие объявления</h2>
              </div>
              <Link href={`/search?species=${animal.species}`} className="btn btn-secondary btn-sm">
                Смотреть всех <ArrowIcon width={16} height={16} />
              </Link>
            </div>
            <div className="listing-grid">
              {related.map((item) => (
                <ListingCard key={item.public_id} listing={item} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
