import type { Metadata } from "next";
import Link from "next/link";

import { ChatIcon, PawIcon } from "@/components/icons";
import { requireMe } from "@/lib/auth-server";
import { getConversationList } from "@/lib/data";
import { formatDateTime, initials } from "@/lib/format";

export const metadata: Metadata = {
  title: "Сообщения",
  robots: { index: false, follow: false },
};

export default async function ChatsPage() {
  await requireMe("/account/chats");
  const conversations = await getConversationList();
  const items = conversations?.items ?? [];

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Общение</span>
          <h1>Сообщения</h1>
          <p className="muted">
            Переписка хранится на сервере и доступна на сайте, в боте и Mini App. Контакты остаются
            скрытыми, пока вы сами ими не поделитесь.
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty-state">
          <ChatIcon width={44} height={44} />
          <h2>Переписок пока нет</h2>
          <p>
            Напишите владельцу из объявления или дождитесь взаимного совпадения — диалог появится
            здесь.
          </p>
          <Link href="/search" className="btn btn-primary">
            Смотреть объявления
          </Link>
        </div>
      ) : (
        <div className="chat-index">
          {items.map((chat) => (
            <Link
              href={`/account/chats/${chat.public_id}`}
              className="chat-index-row"
              key={chat.public_id}
            >
              <span className="chat-index-avatar">
                {chat.listing?.primary_photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={chat.listing.primary_photo_url} alt="" />
                ) : chat.listing ? (
                  <PawIcon width={24} height={24} />
                ) : (
                  initials(chat.counterpart.display_name)
                )}
              </span>
              <span className="grow">
                <span className="chat-item-top">
                  <strong>{chat.counterpart.display_name ?? "Владелец"}</strong>
                  <span className="muted">
                    {chat.last_message_at ? formatDateTime(chat.last_message_at) : ""}
                  </span>
                </span>
                <span className="chat-index-listing">
                  {chat.listing
                    ? `${chat.listing.animal_name} · ${chat.listing.title}`
                    : "Совпадение"}
                </span>
                <span className="chat-item-preview">
                  {chat.last_message
                    ? `${chat.last_message.mine ? "Вы: " : ""}${chat.last_message.body}`
                    : "Диалог открыт — напишите первым"}
                </span>
              </span>
              {chat.unread_count > 0 && <span className="chat-unread">{chat.unread_count}</span>}
              {chat.blocked && <span className="chip chip-danger">Заблокирован</span>}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
