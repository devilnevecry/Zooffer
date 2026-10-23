"use client";

import { useState } from "react";

import { useToast } from "../toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime } from "@/lib/format";
import type { AdminSetting, AdminSettings } from "@/lib/types";

const labels: Record<string, { title: string; hint: string }> = {
  free_daily_swipes: {
    title: "Бесплатные свайпы в день",
    hint: "Общий лимит для сайта, бота и Mini App. Целое число от 0 до 1000.",
  },
  support_email: {
    title: "E-mail поддержки",
    hint: "Показывается в юридических документах и письмах.",
  },
  enable_telegram: {
    title: "Telegram-канал",
    hint: "true или false. Включает вход и уведомления через Telegram после настройки бота.",
  },
  enable_glass: {
    title: "Стеклянные эффекты",
    hint: "true или false. Декоративный слой интерфейса; не влияет на данные.",
  },
};

export function SettingsEditor({
  initial,
  canWrite,
}: {
  initial: AdminSettings;
  canWrite: boolean;
}) {
  const showToast = useToast();
  const [items, setItems] = useState(initial.items);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const save = async (item: AdminSetting) => {
    const value = draft[item.key] ?? item.value;
    setSavingKey(item.key);
    try {
      const updated = await api<AdminSetting>(`/api/v1/admin/settings/${item.key}`, {
        method: "PUT",
        body: { value },
      });
      setItems((current) =>
        current.map((entry) => (entry.key === updated.key ? updated : entry)),
      );
      setDraft((current) => {
        const copy = { ...current };
        delete copy[item.key];
        return copy;
      });
      showToast("Настройка сохранена", "success");
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось сохранить настройку", "error");
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <div className="settings-stack">
      {!canWrite && (
        <p className="notice compact-notice">
          Изменять системные настройки может только суперадминистратор. Значения
          доступны для чтения.
        </p>
      )}
      {items.map((item) => {
        const meta = labels[item.key] ?? { title: item.key, hint: "" };
        const value = draft[item.key] ?? item.value;
        const changed = value !== item.value;
        return (
          <section className="settings-card" key={item.key}>
            <div className="card-head">
              <div>
                <h2>{meta.title}</h2>
                <p>{meta.hint}</p>
              </div>
              {item.updated_at && (
                <span className="muted small">{formatDateTime(item.updated_at)}</span>
              )}
            </div>
            <div className="inline-field">
              <input
                className="input"
                value={value}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, [item.key]: event.target.value }))
                }
                disabled={!canWrite}
                aria-label={meta.title}
              />
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!canWrite || !changed || savingKey === item.key}
                onClick={() => void save(item)}
              >
                {savingKey === item.key ? "Сохраняем…" : "Сохранить"}
              </button>
            </div>
            <p className="field-hint">
              Ключ: <code>{item.key}</code>
            </p>
          </section>
        );
      })}
    </div>
  );
}
