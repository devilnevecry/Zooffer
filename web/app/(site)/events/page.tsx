import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "События",
  description: "Мероприятия для владельцев питомцев на Zooffer.",
};

export default async function EventsPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/events");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>События</h1>
        {items.length === 0 ? (
          <p>Пока нет опубликованных событий.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.title ?? "")}</strong> — {String(item.event_type ?? "")}
                {item.description ? <p>{String(item.description)}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
