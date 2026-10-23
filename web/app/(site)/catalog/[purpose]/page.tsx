import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SearchResults } from "@/components/search-results";
import { getDictionaries } from "@/lib/data";
import type { Purpose } from "@/lib/types";

const catalogPurposes: Record<string, Purpose[]> = {
  sale: ["sale"],
  mating: ["mating"],
  breeding_pedigree: ["breeding_pedigree"],
  adoption: ["adoption", "rehoming"],
};

const titles: Record<string, string> = {
  sale: "Животные в продаже",
  mating: "Вязка животных",
  breeding_pedigree: "Племенное разведение",
  adoption: "Пристройство животных",
};

const descriptions: Record<string, string> = {
  sale: "Животные от владельцев и питомников: проверяйте документы, здоровье и условия перед покупкой.",
  mating: "Найдите пару для своего питомца с учётом вида, породы и здоровья.",
  breeding_pedigree: "Племенные пары с родословной и документами.",
  adoption: "Животные, которым нужен новый дом. Пристройство без цены.",
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ purpose: string }>;
}): Promise<Metadata> {
  const { purpose } = await params;
  if (!catalogPurposes[purpose]) return {};
  return {
    title: titles[purpose],
    description: descriptions[purpose],
    alternates: { canonical: `/catalog/${purpose}` },
  };
}

export default async function CatalogPage({
  params,
  searchParams,
}: {
  params: Promise<{ purpose: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { purpose } = await params;
  const purposes = catalogPurposes[purpose];
  if (!purposes) notFound();
  const search = await searchParams;
  const dictionaries = await getDictionaries();
  return (
    <SearchResults
      params={search}
      dictionaries={dictionaries}
      basePath={`/catalog/${purpose}`}
      fixedPurposes={purposes}
    />
  );
}
