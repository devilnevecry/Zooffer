import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Вопросы и ответы",
  description: "Q&A сообщество Zooffer.",
};

export default async function QaPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/qa/questions");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Вопросы и ответы</h1>
        {items.length === 0 ? (
          <p>Пока нет вопросов.</p>
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
