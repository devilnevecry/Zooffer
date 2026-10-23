import type { Metadata } from "next";

import { SearchResults } from "@/components/search-results";
import { getDictionaries } from "@/lib/data";

type PageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const metadata: Metadata = {
  title: "Поиск животных",
  description:
    "Поиск животных по виду, породе, полу, возрасту, городу и цене. Актуальные объявления на Zooffer.",
  alternates: { canonical: "/search" },
};

export default async function SearchPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const dictionaries = await getDictionaries();
  return <SearchResults params={params} dictionaries={dictionaries} basePath="/search" />;
}
