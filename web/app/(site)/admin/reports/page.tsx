import { ReportQueue } from "@/components/admin/report-queue";
import { serverFetch } from "@/lib/api";
import type { AdminReportList } from "@/lib/types";

export default async function AdminReportsPage() {
  const data = await serverFetch<AdminReportList>("/api/v1/admin/reports?status=open");

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к жалобам</h1>
        <p>Проверьте роль и двухфакторную аутентификацию.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Безопасность</span>
          <h1>Жалобы пользователей</h1>
          <p className="muted">
            Жалобы приходят из объявлений и переписки. Контакты автора жалобы не раскрываются
            публично.
          </p>
        </div>
      </div>
      <ReportQueue initial={data} />
    </>
  );
}
