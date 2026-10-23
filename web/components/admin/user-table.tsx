"use client";

import { useEffect, useState } from "react";

import { useAuth } from "../auth-provider";
import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime } from "@/lib/format";
import type { AdminUser, AdminUserList } from "@/lib/types";

const roles = ["user", "moderator", "admin", "superadmin"];
const statuses = ["active", "suspended", "deleted"];

export function UserTable({ initial }: { initial: AdminUserList }) {
  const { user: me } = useAuth();
  const showToast = useToast();
  const [items, setItems] = useState(initial.items);
  const [total, setTotal] = useState(initial.total);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState<Record<string, { role: string; status: string }>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    if (!query) return;
    const timer = window.setTimeout(() => {
      setLoading(true);
      api<AdminUserList>(`/api/v1/admin/users?q=${encodeURIComponent(query.trim())}`)
        .then((data) => {
          setItems(data.items);
          setTotal(data.total);
        })
        .catch((err) => {
          showToast(err instanceof ClientApiError ? err.message : "Не удалось найти пользователей", "error");
        })
        .finally(() => setLoading(false));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [query, showToast]);

  const save = async (item: AdminUser) => {
    const next = draft[item.public_id] ?? { role: item.role, status: item.status };
    setSavingId(item.public_id);
    try {
      const updated = await api<AdminUser>(`/api/v1/admin/users/${item.public_id}`, {
        method: "PATCH",
        body: { role: next.role, status: next.status },
      });
      setItems((current) =>
        current.map((entry) => (entry.public_id === updated.public_id ? updated : entry)),
      );
      setDraft((current) => {
        const copy = { ...current };
        delete copy[item.public_id];
        return copy;
      });
      showToast("Пользователь обновлён", "success");
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось обновить пользователя", "error");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <>
      <div className="admin-toolbar">
        <form className="admin-search" onSubmit={(event) => event.preventDefault()}>
          <input
            className="input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Имя, фамилия или e-mail"
            aria-label="Поиск пользователей"
          />
        </form>
        <span className="muted small">{loading ? "Ищем…" : `Всего: ${total}`}</span>
      </div>

      <div className="admin-table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Пользователь</th>
              <th>E-mail</th>
              <th>Город</th>
              <th>Роль</th>
              <th>Статус</th>
              <th>2FA</th>
              <th>Регистрация</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const value = draft[item.public_id] ?? { role: item.role, status: item.status };
              const changed = value.role !== item.role || value.status !== item.status;
              const isSelf = me?.public_id === item.public_id;
              return (
                <tr key={item.public_id}>
                  <td>
                    <strong>{item.display_name ?? "Владелец"}</strong>
                    <small className="admin-table-sub">
                      {item.listings_count} объявл.
                    </small>
                  </td>
                  <td>{item.email ?? "—"}</td>
                  <td>{item.city_name ?? "—"}</td>
                  <td>
                    <select
                      className="select select-sm"
                      value={value.role}
                      disabled={isSelf}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          [item.public_id]: { ...value, role: event.target.value },
                        }))
                      }
                      aria-label={`Роль ${item.display_name ?? ""}`}
                    >
                      {roles.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      className="select select-sm"
                      value={value.status}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          [item.public_id]: { ...value, status: event.target.value },
                        }))
                      }
                      aria-label={`Статус ${item.display_name ?? ""}`}
                    >
                      {statuses.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>{item.mfa_enabled ? "Вкл." : "Выкл."}</td>
                  <td>{formatDateTime(item.created_at)}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={!changed || savingId === item.public_id}
                      onClick={() => void save(item)}
                    >
                      {savingId === item.public_id ? "…" : "Сохранить"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {items.length === 0 && <p className="muted">Пользователи не найдены.</p>}
    </>
  );
}
