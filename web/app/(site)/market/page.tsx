import type { Metadata } from "next";

import { serverFetch } from "@/lib/api";

export const metadata: Metadata = {
  title: "Маркет",
  description: "Зоомагазины и товары на Zooffer.",
};

export default async function MarketPage() {
  const [shops, products] = await Promise.all([
    serverFetch<Record<string, unknown>>("/api/v1/market/shops"),
    serverFetch<Record<string, unknown>>("/api/v1/market/products"),
  ]);
  const shopItems = Array.isArray(shops?.items) ? (shops.items as Record<string, unknown>[]) : [];
  const productItems = Array.isArray(products?.items) ? (products.items as Record<string, unknown>[]) : [];
  return (
    <div className="page page-tight">
      <div className="container">
        <h1>Маркет</h1>
        <h2>Магазины</h2>
        {shopItems.length === 0 ? (
          <p>Пока нет магазинов.</p>
        ) : (
          <ul>
            {shopItems.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.name ?? "")}</strong>
                {item.description ? <p>{String(item.description)}</p> : null}
              </li>
            ))}
          </ul>
        )}
        <h2>Товары</h2>
        {productItems.length === 0 ? (
          <p>Пока нет товаров.</p>
        ) : (
          <ul>
            {productItems.map((item) => (
              <li key={String(item.public_id)}>
                <strong>{String(item.title ?? "")}</strong> — {String(item.price_kopecks ?? "")} коп.
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
