import type { Metadata } from "next";
import Link from "next/link";

import { PlusIcon } from "@/components/icons";
import { ListingManager } from "@/components/listing-manager";
import { serverFetch } from "@/lib/api";
import { requireMe } from "@/lib/auth-server";
import type { OwnerListing } from "@/lib/types";

export const metadata: Metadata = {
  title: "Мои объявления",
  robots: { index: false, follow: false },
};

export default async function MyListingsPage() {
  await requireMe("/account/listings");
  const listings =
    (await serverFetch<OwnerListing[]>("/api/v1/listings", { allow401: true })) ?? [];

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Объявления</span>
          <h1>Мои объявления</h1>
          <p className="muted">
            Публикуйте, приостанавливайте и обновляйте объявления. После правок объявление проходит
            повторную проверку.
          </p>
        </div>
        <Link href="/account/listings/new" className="btn btn-primary">
          <PlusIcon /> Новое объявление
        </Link>
      </div>
      <ListingManager initial={listings} />
    </>
  );
}
