import Link from "next/link";

import { ArrowIcon } from "@/components/icons";
import { serverFetch } from "@/lib/api";
import { formatDateTime, formatPrice } from "@/lib/format";
import type { AdminDashboard } from "@/lib/types";

const actionLabels: Record<string, string> = {
  "listing.approve": "Объявление одобрено",
  "listing.reject": "Объявление отклонено",
  "report.resolved": "Жалоба решена",
  "report.dismissed": "Жалоба отклонена",
  "report.in_review": "Жалоба на проверке",
  "user.update": "Профиль пользователя обновлён",
  "support.reply": "Ответ поддержки",
  "settings.update": "Настройка изменена",
};

export default async function AdminDashboardPage() {
  const data = await serverFetch<AdminDashboard>("/api/v1/admin/dashboard");

  if (!data) {
    return (
      <div className="empty-state">
        <h1>Панель недоступна</h1>
        <p>Не удалось получить данные. Проверьте права и двухфакторную аутентификацию.</p>
      </div>
    );
  }

  const stats = data.stats;

  return (
    <>
      <div className="account-head">
        <div>
          <span className="eyebrow">Служебный раздел</span>
          <h1>Сводка Zooffer</h1>
          <p className="muted">Ключевые показатели и последние действия сотрудников.</p>
        </div>
        <Link href="/admin/moderation" className="btn btn-primary">
          Очередь модерации <ArrowIcon width={16} height={16} />
        </Link>
      </div>

      <div className="admin-stat-grid">
        <div className="stat">
          <strong>{stats.users_total}</strong>
          <span>пользователей</span>
          <small>+{stats.users_new_week} за неделю</small>
        </div>
        <div className="stat">
          <strong>{stats.listings_published}</strong>
          <span>опубликованных объявлений</span>
          <small>{stats.listings_pending} ждут проверки</small>
        </div>
        <div className="stat">
          <strong>{stats.reports_open}</strong>
          <span>открытых жалоб</span>
          <small>{stats.support_open} обращений в поддержку</small>
        </div>
        <div className="stat">
          <strong>{stats.subscriptions_active}</strong>
          <span>активных подписок</span>
          <small>Выручка за 30 дней: {formatPrice(stats.revenue_kopecks_30d)}</small>
        </div>
        <div className="stat">
          <strong>{stats.swipes_today}</strong>
          <span>свайпов сегодня</span>
          <small>{stats.matches_total} взаимных совпадений</small>
        </div>
      </div>

      <section className="dashboard-card">
        <div className="card-head">
          <div>
            <h2>Последние действия</h2>
            <p>Журнал доступен полностью в разделе «Журнал».</p>
          </div>
          <Link href="/admin/audit" className="text-link">
            Весь журнал <ArrowIcon width={15} height={15} />
          </Link>
        </div>
        {data.recent_actions.length === 0 ? (
          <p className="muted">Действий пока нет.</p>
        ) : (
          <div className="compact-list">
            {data.recent_actions.map((item, index) => (
              <div className="compact-row" key={`${item.created_at}-${index}`}>
                <span className="grow">
                  <strong>{actionLabels[item.action] ?? item.action}</strong>
                  <small>
                    {item.object_type}
                    {item.object_id ? ` · ${item.object_id.slice(0, 8)}` : ""} ·{" "}
                    {formatDateTime(item.created_at)}
                  </small>
                </span>
                {item.actor_role && <span className="chip">{item.actor_role}</span>}
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
