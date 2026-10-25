import type { Metadata } from "next";

import { FavoriteManager } from "@/components/favorite-manager";
import { requireMe } from "@/lib/auth-server";
import { getFavoriteList } from "@/lib/data";

export const metadata: Metadata = {
  title: "Избранное",
  robots: { index: false, follow: false },
};

export default async function FavoritesPage() {
  await requireMe("/account/favorites");
  const favorites = await getFavoriteList();
  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Сохранённое</span>
          <h1>Избранное</h1>
          <p className="muted">
            Объявления, которые вы отметили. Сохранение не открывает чат и не раскрывает контакты
            владельца.
          </p>
        </div>
      </div>
      <FavoriteManager initial={favorites?.items ?? []} />
    </>
  );
}
