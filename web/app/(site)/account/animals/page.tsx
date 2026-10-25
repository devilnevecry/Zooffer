import type { Metadata } from "next";
import Link from "next/link";

import { AnimalManager } from "@/components/animal-manager";
import { PlusIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";
import { getDictionaries, getOwnerAnimals } from "@/lib/data";

export const metadata: Metadata = {
  title: "Мои животные",
  robots: { index: false, follow: false },
};

export default async function AccountAnimalsPage() {
  await requireMe("/account/animals");
  const [animals, dictionaries] = await Promise.all([getOwnerAnimals(), getDictionaries()]);
  const items = animals?.items ?? [];

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Анкеты</span>
          <h1>Мои животные</h1>
          <p className="muted">
            Фотографии, здоровье и родословная хранятся в одном профиле. Документы видны только вам
            и модерации.
          </p>
        </div>
        <Link href="/account/listings/new" className="btn btn-primary">
          <PlusIcon /> Новое объявление
        </Link>
      </div>
      <AnimalManager initial={items} dictionaries={dictionaries} />
    </>
  );
}
