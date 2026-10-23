import { UserTable } from "@/components/admin/user-table";
import { serverFetch } from "@/lib/api";
import type { AdminUserList } from "@/lib/types";

export default async function AdminUsersPage() {
  const data = await serverFetch<AdminUserList>("/api/v1/admin/users");

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к пользователям</h1>
        <p>Раздел доступен администраторам и суперадминистраторам с включённой 2FA.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Аккаунты</span>
          <h1>Пользователи</h1>
          <p className="muted">
            Роли и статусы меняются только сотрудниками. Контакты видны лишь в этом
            защищённом разделе.
          </p>
        </div>
      </div>
      <UserTable initial={data} />
    </>
  );
}
