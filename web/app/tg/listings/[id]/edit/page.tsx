import { MiniListingWizard } from "@/components/miniapp/wizard";

export default async function MiniAppEditListingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <MiniListingWizard listingId={id} />;
}
