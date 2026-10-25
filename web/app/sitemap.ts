import type { MetadataRoute } from "next";

import { getHome, searchListings } from "@/lib/data";

const purposes = ["sale", "mating", "breeding_pedigree", "adoption", "rehoming"];
const legal = ["rules", "privacy", "terms", "personal-data", "requisites", "offer"];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
  const now = new Date();
  const [home, latest] = await Promise.all([
    getHome(),
    searchListings({ limit: 100, sort: "newest" }),
  ]);

  const staticEntries: MetadataRoute.Sitemap = [
    { url: `${base}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${base}/discovery`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${base}/search`, lastModified: now, changeFrequency: "daily", priority: 0.9 },
    { url: `${base}/partners`, lastModified: now, changeFrequency: "weekly", priority: 0.5 },
    { url: `${base}/support`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    ...legal.map((slug) => ({
      url: `${base}/legal/${slug}`,
      lastModified: now,
      changeFrequency: "yearly" as const,
      priority: 0.2,
    })),
    ...purposes.map((purpose) => ({
      url: `${base}/catalog/${purpose}`,
      lastModified: now,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
  ];

  const listingEntries: MetadataRoute.Sitemap = (latest?.items ?? []).map((item) => ({
    url: `${base}/listing/${item.slug}`,
    lastModified: item.published_at ? new Date(item.published_at) : now,
    changeFrequency: "weekly",
    priority: 0.6,
    images: item.primary_photo ? [item.primary_photo.url] : undefined,
  }));

  // Ensure the homepage categories are represented even when a feed is empty.
  void home;

  return [...staticEntries, ...listingEntries];
}
