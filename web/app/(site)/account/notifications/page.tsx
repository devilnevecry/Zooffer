import type { Metadata } from "next";

import { NotificationCenter } from "@/components/notification-center";
import { requireMe } from "@/lib/auth-server";
import { getNotificationList } from "@/lib/data";

export const metadata: Metadata = {
  title: "Уведомления",
  robots: { index: false, follow: false },
};

export default async function NotificationsPage() {
  await requireMe("/account/notifications");
  const notifications = await getNotificationList();
  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">События</span>
          <h1>Уведомления</h1>
          <p className="muted">
            Только важное: ответы, совпадения, проверка объявлений и состояние аккаунта. Рекламные
            рассылки можно отключить в настройках.
          </p>
        </div>
      </div>
      <NotificationCenter initial={notifications ?? { items: [], unread_count: 0 }} />
    </>
  );
}
