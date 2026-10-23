"use client";

import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { ChatIcon } from "./icons";
import { Modal } from "./modal";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import type { ConversationDetail } from "@/lib/types";

export function InquiryButton({
  listingId,
  listingTitle,
  ownerName,
  className = "btn btn-primary",
  chatsPath = "/account/chats",
}: {
  listingId: string;
  listingTitle: string;
  ownerName: string | null;
  className?: string;
  chatsPath?: string;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const showToast = useToast();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState(
    `Здравствуйте${ownerName ? `, ${ownerName}` : ""}! Меня заинтересовало объявление «${listingTitle}». Подскажите, пожалуйста, что важно знать о животном?`,
  );
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const openDialog = () => {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setOpen(true);
  };

  const send = async (event: React.FormEvent) => {
    event.preventDefault();
    setSending(true);
    setError("");
    try {
      const conversation = await api<ConversationDetail>("/api/v1/conversations", {
        method: "POST",
        body: { listing_public_id: listingId, message: message.trim() || null },
      });
      showToast("Сообщение отправлено");
      router.push(`${chatsPath}/${conversation.conversation.public_id}`);
    } catch (err) {
      setError(
        err instanceof ClientApiError ? err.message : "Не удалось начать переписку. Попробуйте ещё раз.",
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <>
      <button type="button" className={className} onClick={openDialog}>
        <ChatIcon /> Написать владельцу
      </button>
      <Modal open={open} onClose={() => setOpen(false)} title="Начать переписку">
        <form onSubmit={send}>
          <p className="modal-lead">
            Сообщение придёт владельцу объявления. Не отправляйте предоплату и не
            переходите по подозрительным ссылкам.
          </p>
          <div className="field">
            <label htmlFor="inquiry-message">Сообщение</label>
            <textarea
              id="inquiry-message"
              className="textarea"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              maxLength={4000}
              rows={5}
            />
            <span className="field-hint">{message.length} / 4000</span>
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="btn-row">
            <button type="submit" className="btn btn-primary" disabled={sending}>
              {sending ? "Отправляем…" : "Отправить"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>
              Отмена
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
