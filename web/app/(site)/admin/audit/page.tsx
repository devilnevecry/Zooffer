import { serverFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AdminAuditList } from "@/lib/types";

export default async function AdminAuditPage() {
  const data = await serverFetch<AdminAuditList>("/api/v1/admin/audit?limit=200");

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к журналу</h1>
        <p>Проверьте роль и двухфакторную аутентификацию.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Аудит</span>
          <h1>Журнал действий</h1>
          <p className="muted">
            Записи неизменяемы на уровне приложения. В журнал не попадают контакты и содержимое
            переписки.
          </p>
        </div>
      </div>

      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Время</th>
              <th>Действие</th>
              <th>Объект</th>
              <th>Роль</th>
              <th>Метаданные</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr key={item.id}>
                <td>{formatDateTime(item.created_at)}</td>
                <td>
                  <strong>{item.action}</strong>
                </td>
                <td>
                  {item.object_type}
                  {item.object_id ? ` · ${item.object_id.slice(0, 12)}` : ""}
                </td>
                <td>{item.actor_role ?? "—"}</td>
                <td>
                  <code className="admin-meta-json">
                    {item.metadata ? JSON.stringify(item.metadata) : "—"}
                  </code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.items.length === 0 && <p className="muted">Записей пока нет.</p>}
    </>
  );
}
