import Link from "next/link";

import { PURPOSE_LABELS } from "@/lib/format";
import type { CategoryCount, Purpose } from "@/lib/types";

import { ArrowIcon, HeartIcon, PawIcon, ShieldIcon, SparkIcon } from "./icons";

const icons = {
  sale: PawIcon,
  mating: HeartIcon,
  breeding_pedigree: ShieldIcon,
  adoption: SparkIcon,
} as const;

export function categoryCards(categories: CategoryCount[]) {
  const byPurpose = new Map(categories.map((item) => [item.purpose, item.count]));
  return [
    {
      key: "sale",
      title: PURPOSE_LABELS.sale,
      description: "Проверенные объявления от владельцев и питомников",
      count: byPurpose.get("sale") ?? 0,
      href: "/catalog/sale",
      purposes: ["sale"] as Purpose[],
    },
    {
      key: "mating",
      title: PURPOSE_LABELS.mating,
      description: "Знакомства для будущих малышей и здоровой генетики",
      count: byPurpose.get("mating") ?? 0,
      href: "/catalog/mating",
      purposes: ["mating"] as Purpose[],
    },
    {
      key: "breeding_pedigree",
      title: "Племенное разведение",
      description: "Пары с подтверждённой родословной и документами",
      count: byPurpose.get("breeding_pedigree") ?? 0,
      href: "/catalog/breeding_pedigree",
      purposes: ["breeding_pedigree"] as Purpose[],
    },
    {
      key: "adoption",
      title: "Пристройство",
      description: "Дом, передержка и новая жизнь — без цены",
      count: (byPurpose.get("adoption") ?? 0) + (byPurpose.get("rehoming") ?? 0),
      href: "/catalog/adoption",
      purposes: ["adoption", "rehoming"] as Purpose[],
    },
  ];
}

export function CategoryGrid({ categories }: { categories: CategoryCount[] }) {
  const cards = categoryCards(categories);
  return (
    <div className="category-grid">
      {cards.map((card) => {
        const Icon = icons[card.key as keyof typeof icons] ?? PawIcon;
        return (
          <Link key={card.key} href={card.href} className="category-card">
            <div>
              <span className="category-icon" aria-hidden="true">
                <Icon />
              </span>
              <h3>{card.title}</h3>
              <p className="category-description">{card.description}</p>
              <p className="count">
                {card.count > 0
                  ? `${card.count.toLocaleString("ru-RU")} ${
                      card.count === 1 ? "объявление" : "объявлений"
                    }`
                  : "Пока нет объявлений"}
              </p>
            </div>
            <span className="category-arrow" aria-hidden="true">
              <ArrowIcon />
            </span>
          </Link>
        );
      })}
    </div>
  );
}
