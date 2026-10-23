import { SupportQueue } from "@/components/admin/support-queue";
import { serverFetch } from "@/lib/api";
import type { AdminSupportList } from "@/lib/types";

export default async function AdminSupportPage() {
  const data = await serverFetch<AdminSupportList>("/api/v1/admin/support");

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к поддержке</h1>
        <p>Проверьте роль и двухфакторную аутентификацию.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Поддержка</span>
          <h1>Обращения</h1>
          <p className="muted">
            Отвечайте по существу и не запрашивайте пароли или коды подтверждения.
          </p>
        </div>
      </div>
      <SupportQueue initial={data} />
    </>
  );
}
