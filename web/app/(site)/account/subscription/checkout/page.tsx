import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { CheckoutPanel } from "@/components/checkout";
import { requireMe } from "@/lib/auth-server";

export const metadata: Metadata = {
  title: "Оплата подписки",
  robots: { index: false, follow: false },
};

export default async function CheckoutPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  await requireMe("/account/subscription");
  const params = await searchParams;
  const raw = params.order;
  const orderId = Array.isArray(raw) ? raw[0] : raw;
  if (!orderId) redirect("/account/subscription");

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Zooffer Plus</span>
          <h1>Оплата</h1>
          <p className="muted">
            Проверьте тариф и сумму. Платёжные данные вводятся только у платёжного провайдера.
          </p>
        </div>
      </div>
      <CheckoutPanel orderId={orderId} />
    </>
  );
}
