import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Видео",
  description: "Видеолента Zooffer.",
};

export default async function VideoPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/videos");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Видео</h1>
        {items.length === 0 ? (
          <p>Пока нет видео.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.caption ?? "")}</strong>
                <small>
                  {" "}
                  просмотры: {String(item.views ?? 0)}, лайки: {String(item.likes ?? 0)}
                </small>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
