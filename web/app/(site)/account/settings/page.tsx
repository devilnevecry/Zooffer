import type { Metadata } from "next";

import { SettingsPanel } from "@/components/settings-panel";
import { requireMe } from "@/lib/auth-server";
import {
  getBlockedUsers,
  getDictionaries,
  getNotificationPreferences,
  getSessions,
} from "@/lib/data";

export const metadata: Metadata = {
  title: "Настройки и приватность",
  robots: { index: false, follow: false },
};

export default async function SettingsPage() {
  const me = await requireMe("/account/settings");
  const [dictionaries, sessions, preferences, blocked] = await Promise.all([
    getDictionaries(),
    getSessions(),
    getNotificationPreferences(),
    getBlockedUsers(),
  ]);

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Приватность</span>
          <h1>Настройки</h1>
          <p className="muted">
            Публичное имя, уведомления, сеансы и данные аккаунта — в одном месте.
          </p>
        </div>
      </div>
      <SettingsPanel
        user={me.user}
        dictionaries={dictionaries}
        sessions={sessions?.items ?? []}
        preferences={preferences ?? { items: [] }}
        blocked={blocked?.items ?? []}
      />
    </>
  );
}
