import { SettingsEditor } from "@/components/admin/settings-editor";
import { serverFetch } from "@/lib/api";
import { requireMe } from "@/lib/auth-server";
import type { AdminSettings } from "@/lib/types";

export default async function AdminSettingsPage() {
  const [me, data] = await Promise.all([
    requireMe("/admin/settings"),
    serverFetch<AdminSettings>("/api/v1/admin/settings"),
  ]);

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к настройкам</h1>
        <p>Проверьте роль и двухфакторную аутентификацию.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Система</span>
          <h1>Настройки</h1>
          <p className="muted">
            Изменения фиксируются в журнале. Лимит свайпов действует на всех клиентах одновременно.
          </p>
        </div>
      </div>
      <SettingsEditor initial={data} canWrite={me.user.role === "superadmin"} />
    </>
  );
}
