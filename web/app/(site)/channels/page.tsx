import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Каналы",
  description: "Каналы приютов и сообществ на Zooffer.",
};

export default async function ChannelsPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/channels");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Каналы</h1>
        {items.length === 0 ? (
          <p>Пока нет каналов.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.title ?? "")}</strong>
                {item.description ? <p>{String(item.description)}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
