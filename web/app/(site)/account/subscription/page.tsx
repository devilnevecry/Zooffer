import type { Metadata } from "next";

import { SubscriptionManager } from "@/components/subscription-manager";
import { requireMe } from "@/lib/auth-server";
import { getPlans, getSubscriptionState } from "@/lib/data";

export const metadata: Metadata = {
  title: "Подписка",
  robots: { index: false, follow: false },
};

export default async function SubscriptionPage() {
  await requireMe("/account/subscription");
  const [state, plans] = await Promise.all([getSubscriptionState(), getPlans()]);

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Zooffer Plus</span>
          <h1>Подписка</h1>
          <p className="muted">
            План, лимиты и история продления. Управление доступно без обращения в
            поддержку.
          </p>
        </div>
      </div>
      <SubscriptionManager
        initial={
          state ?? {
            status: "none",
            plan_code: null,
            plan_name: null,
            current_period_end: null,
            cancel_at_period_end: false,
            entitlements: [],
            quota_limit: 0,
            quota_unlimited: false,
            payments_available: false,
          }
        }
        plans={plans?.items ?? []}
      />
    </>
  );
}
