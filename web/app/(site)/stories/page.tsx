import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Истории",
  description: "Истории спасения и ухода на Zooffer.",
};

export default async function StoriesPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/stories");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Истории</h1>
        {items.length === 0 ? (
          <p>Пока нет опубликованных историй.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.title ?? "")}</strong>
                {item.body ? <p>{String(item.body)}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
