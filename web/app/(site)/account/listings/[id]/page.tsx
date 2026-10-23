import { redirect } from "next/navigation";

export default async function ListingDetailRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/account/listings/${id}/edit`);
}
