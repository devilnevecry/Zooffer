import { ModerationBoard } from "@/components/admin/moderation-board";
import { serverFetch } from "@/lib/api";
import type { AdminListingList } from "@/lib/types";

export default async function AdminModerationPage() {
  const data = await serverFetch<AdminListingList>(
    "/api/v1/admin/listings?status=pending_moderation",
  );

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к модерации</h1>
        <p>Проверьте роль и двухфакторную аутентификацию.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Модерация</span>
          <h1>Объявления</h1>
          <p className="muted">
            Проверяйте фото, контакты в тексте и признаки мошенничества до публикации.
          </p>
        </div>
      </div>
      <ModerationBoard initial={data} />
    </>
  );
}
