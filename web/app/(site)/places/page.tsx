import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Места для питомцев",
  description: "Карта pet-friendly мест на Zooffer.",
};

export default async function PlacesPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/places");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Места для питомцев</h1>
        {items.length === 0 ? (
          <p>Пока нет одобренных мест.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.name ?? "")}</strong> — {String(item.category ?? "")}
                {item.description ? <p>{String(item.description)}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
