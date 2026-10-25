import { MiniChat } from "@/components/miniapp/chat";

export default async function MiniAppChatPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MiniChat conversationId={id} />;
}
