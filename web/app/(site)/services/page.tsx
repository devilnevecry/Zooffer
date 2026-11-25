import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Услуги для питомцев",
  description: "Каталог услуг для животных на Zooffer.",
};

export default async function ServicesPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/services/profiles");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Услуги для питомцев</h1>
        {items.length === 0 ? (
          <p>Пока нет одобренных профилей.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.title ?? "")}</strong> — {String(item.category ?? "")}
                {item.description ? <p>{String(item.description)}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
