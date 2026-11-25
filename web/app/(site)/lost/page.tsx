import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Потерянные питомцы",
  description: "Объявления о потерянных и найденных питомцах на Zooffer.",
};

export default async function LostPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/lost");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Потерянные питомцы</h1>
        {items.length === 0 ? (
          <p>Пока нет активных объявлений.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.title ?? "")}</strong> — {String(item.status ?? "")}
                {item.description ? <p>{String(item.description)}</p> : null}
                <small>{String((item.owner as Record<string, unknown> | undefined)?.display_name ?? "Владелец")}</small>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
