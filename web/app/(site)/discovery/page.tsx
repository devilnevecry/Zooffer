import type { Metadata } from "next";

import { DiscoveryDeck } from "@/components/discovery-deck";
import { getDiscoveryFeed } from "@/lib/data";

export const metadata: Metadata = {
  title: "Подбор животных",
  description:
    "Листайте карточки животных, сохраняйте понравившихся и находите взаимные совпадения на Zooffer.",
  robots: { index: false, follow: true },
};

export default async function DiscoveryPage() {
  const feed = await getDiscoveryFeed();
  return (
    <div className="page page-tight">
      <DiscoveryDeck initialFeed={feed} />
    </div>
  );
}
