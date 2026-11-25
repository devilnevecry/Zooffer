import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Организации",
  description: "Приюты и организации на Zooffer.",
};

export default async function OrganizationsPage() {
  const data = await serverFetch<Record<string, unknown>>("/api/v1/organizations");
  const items = Array.isArray(data?.items) ? (data.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Организации</h1>
        {items.length === 0 ? (
          <p>Пока нет одобренных организаций.</p>
        ) : (
          <ul>
            {items.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.name ?? "")}</strong> — {String(item.org_type ?? "")}
                {item.description ? <p>{String(item.description)}</p> : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
