import { notFound } from "next/navigation";

import { PaymentDetail } from "@/components/admin/payment-detail";
import { serverFetch } from "@/lib/api";
import type { AdminPaymentDetail } from "@/lib/types";

export default async function AdminPaymentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await serverFetch<AdminPaymentDetail>(`/api/v1/admin/payments/${id}`);
  if (!detail) notFound();
  return <PaymentDetail initial={detail} />;
}
