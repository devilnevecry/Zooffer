import Link from "next/link";

import { serverFetch } from "@/lib/api";
import { formatDateTime, formatPrice } from "@/lib/format";
import type { AdminPaymentList } from "@/lib/types";

const statusLabels: Record<string, string> = {
  pending: "Ожидает",
  paid: "Оплачен",
  canceled: "Отменён",
  refunded: "Возврат",
  failed: "Ошибка",
};

export default async function AdminPaymentsPage() {
  const data = await serverFetch<AdminPaymentList>("/api/v1/admin/payments");

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Нет доступа к платежам</h1>
        <p>Раздел доступен администраторам и суперадминистраторам с включённой 2FA.</p>
      </div>
    );
  }

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Биллинг</span>
          <h1>Платежи</h1>
          <p className="muted">
            Реальные платежи не подключены без merchant-credentials. Здесь отображаются
            только сохранённые заказы, включая тестовые.
          </p>
        </div>
      </div>

      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Пользователь</th>
              <th>План</th>
              <th>Провайдер</th>
              <th>Статус</th>
              <th>Сумма</th>
              <th>Оплачен</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr key={item.public_id}>
                <td>{formatDateTime(item.created_at)}</td>
                <td>{item.user_name ?? "—"}</td>
                <td>{item.plan_code}</td>
                <td>{item.provider}</td>
                <td>{statusLabels[item.status] ?? item.status}</td>
                <td>{formatPrice(item.amount_kopecks)}</td>
                <td>{item.paid_at ? formatDateTime(item.paid_at) : "—"}</td>
                <td>
                  <Link
                    href={`/admin/payments/${item.public_id}`}
                    className="btn btn-ghost btn-sm"
                  >
                    Открыть
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.items.length === 0 && (
        <p className="muted">Заказов нет. Это ожидаемо, пока платёжный провайдер не подключён.</p>
      )}
    </>
  );
}
