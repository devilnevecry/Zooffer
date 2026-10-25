import type { Metadata } from "next";
import Link from "next/link";

import { ListingWizard } from "@/components/listing-wizard";
import { ArrowIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";
import { getDictionaries } from "@/lib/data";

export const metadata: Metadata = {
  title: "Новое объявление",
  robots: { index: false, follow: false },
};

export default async function NewListingPage() {
  await requireMe("/account/listings/new");
  const dictionaries = await getDictionaries();

  return (
    <>
      <nav className="breadcrumbs" aria-label="Навигация">
        <Link href="/account">Аккаунт</Link>
        <span aria-hidden="true">/</span>
        <Link href="/account/listings">Объявления</Link>
        <span aria-hidden="true">/</span>
        <span>Новое</span>
      </nav>
      <div className="account-head">
        <div>
          <span className="eyebrow">Мастер размещения</span>
          <h1>Новое объявление</h1>
          <p className="muted">
            Черновик сохраняется на сервере после каждого шага. Вернуться можно с любого устройства.
          </p>
        </div>
        <Link href="/account/listings" className="btn btn-ghost btn-sm">
          <ArrowIcon width={15} height={15} /> К объявлениям
        </Link>
      </div>
      <ListingWizard dictionaries={dictionaries} />
    </>
  );
}
