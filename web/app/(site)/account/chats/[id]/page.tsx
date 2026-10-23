import type { Metadata } from "next";

import { ChatPanel } from "@/components/chat-panel";
import { serverFetch } from "@/lib/api";
import { requireMe } from "@/lib/auth-server";
import type { ConversationDetail } from "@/lib/types";

export const metadata: Metadata = {
  title: "Переписка",
  robots: { index: false, follow: false },
};

export default async function ChatDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  await requireMe(`/account/chats/${id}`);
  const detail = await serverFetch<ConversationDetail>(
    `/api/v1/conversations/${encodeURIComponent(id)}`,
    { allow401: true, allow404: true },
  );
  return (
    <div className="page-tight">
      <ChatPanel initial={detail} />
    </div>
  );
}
