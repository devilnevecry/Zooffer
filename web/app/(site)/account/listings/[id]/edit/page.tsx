import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ListingWizard } from "@/components/listing-wizard";
import { ArrowIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";
import { getDictionaries, getOwnerAnimals, getOwnerListing } from "@/lib/data";

export const metadata: Metadata = {
  title: "Редактирование объявления",
  robots: { index: false, follow: false },
};

export default async function EditListingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  await requireMe(`/account/listings/${id}/edit`);
  const [listing, animals, dictionaries] = await Promise.all([
    getOwnerListing(id),
    getOwnerAnimals(),
    getDictionaries(),
  ]);
  if (!listing) notFound();

  const animal = animals?.items.find((item) => item.public_id === listing.animal_public_id);
  if (!animal) notFound();

  return (
    <>
      <nav className="breadcrumbs" aria-label="Навигация">
        <Link href="/account">Аккаунт</Link>
        <span aria-hidden="true">/</span>
        <Link href="/account/listings">Объявления</Link>
        <span aria-hidden="true">/</span>
        <span>Редактирование</span>
      </nav>
      <div className="account-head">
        <div>
          <span className="eyebrow">Мастер размещения</span>
          <h1>Редактирование</h1>
          <p className="muted">
            Изменения опубликованного объявления отправляются на повторную проверку, чтобы описание
            не расходилось с фотографиями.
          </p>
        </div>
        <Link href="/account/listings" className="btn btn-ghost btn-sm">
          <ArrowIcon width={15} height={15} /> К объявлениям
        </Link>
      </div>
      <ListingWizard dictionaries={dictionaries} initialListing={listing} initialAnimal={animal} />
    </>
  );
}
