"use client";

import { ChatPanel } from "../chat-panel";
import type { ConversationDetail } from "@/lib/types";

import { MiniError, MiniLoading, useMiniApi } from "./ui";

export function MiniChat({ conversationId }: { conversationId: string }) {
  const { data, loading, error, reload } = useMiniApi<ConversationDetail>(
    conversationId ? `/api/v1/conversations/${encodeURIComponent(conversationId)}` : null,
  );

  if (loading && !data) return <MiniLoading label="Открываем диалог…" />;
  if (error && !data) return <MiniError message={error} onRetry={reload} />;

  return <ChatPanel initial={data} basePath="/tg" listingPath="/tg/listing" compact />;
}
