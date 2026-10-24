import { redirect } from "next/navigation";

import { CheckoutPanel } from "@/components/checkout";

export default async function MiniCheckoutPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const raw = params.order;
  const orderId = Array.isArray(raw) ? raw[0] : raw;
  if (!orderId) redirect("/tg/subscription");

  return (
    <div className="tg-stack">
      <CheckoutPanel
        orderId={orderId}
        backHref="/tg/subscription"
        backLabel="Вернуться к подписке"
      />
    </div>
  );
}
