"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { CheckIcon, DocumentIcon, ShieldIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";
import { formatDateTime } from "@/lib/format";
import type {
  BlockedUser,
  Dictionaries,
  NotificationPreference,
  NotificationPreferenceList,
  SelfUser,
  SessionView,
} from "@/lib/types";

const categoryLabels: Record<string, string> = {
  matches: "Совпадения",
  messages: "Сообщения",
  inquiries: "Запросы по объявлениям",
  listing_moderation: "Статус объявлений",
  subscriptions: "Подписка и платежи",
  partners: "Партнёрские предложения",
  support: "Ответы поддержки",
  security: "Безопасность входа",
};

export function SettingsPanel({
  user,
  dictionaries,
  sessions,
  preferences,
  blocked,
  loginPath = "/login",
  afterDeletePath = "/",
  supportPath = "/support",
}: {
  user: SelfUser;
  dictionaries: Dictionaries | null;
  sessions: SessionView[];
  preferences: NotificationPreferenceList;
  blocked: BlockedUser[];
  loginPath?: string;
  afterDeletePath?: string;
  supportPath?: string;
}) {
  const router = useRouter();
  const showToast = useToast();
  const { refresh } = useAuth();

  const [profile, setProfile] = useState({
    firstName: user.first_name ?? "",
    lastName: user.last_name ?? "",
    cityId: user.city_id ? String(user.city_id) : "",
  });
  const [savingProfile, setSavingProfile] = useState(false);

  const [prefs, setPrefs] = useState(preferences.items);
  const [savingPrefs, setSavingPrefs] = useState(false);

  const [activeSessions, setActiveSessions] = useState(sessions);
  const [blockedUsers, setBlockedUsers] = useState(blocked);
  const [confirmation, setConfirmation] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [mfaEnabled, setMfaEnabled] = useState(user.mfa_enabled);
  const [mfaSetup, setMfaSetup] = useState<{ secret: string; otpauth_url: string } | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaBusy, setMfaBusy] = useState(false);

  const saveProfile = async () => {
    if (!profile.firstName.trim()) {
      showToast("Имя не может быть пустым", "error");
      return;
    }
    setSavingProfile(true);
    try {
      await api<SelfUser>("/api/v1/auth/profile", {
        method: "PATCH",
        body: {
          first_name: profile.firstName.trim(),
          last_name: profile.lastName.trim() || null,
          city_id: profile.cityId ? Number(profile.cityId) : null,
        },
      });
      await refresh();
      showToast("Профиль обновлён", "success");
      router.refresh();
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось сохранить профиль",
        "error",
      );
    } finally {
      setSavingProfile(false);
    }
  };

  const togglePref = (category: string, channel: keyof NotificationPreference) => {
    setPrefs((items) =>
      items.map((item) =>
        item.category === category ? { ...item, [channel]: !item[channel] } : item,
      ),
    );
  };

  const savePreferences = async () => {
    setSavingPrefs(true);
    try {
      const updated = await api<NotificationPreferenceList>("/api/v1/notification-preferences", {
        method: "PUT",
        body: {
          items: prefs.map((item) => ({
            category: item.category,
            in_app: item.in_app,
            telegram: item.telegram,
            email: item.email,
            quiet_from: item.quiet_from,
            quiet_to: item.quiet_to,
          })),
        },
      });
      setPrefs(updated.items);
      showToast("Настройки уведомлений сохранены", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось сохранить настройки",
        "error",
      );
    } finally {
      setSavingPrefs(false);
    }
  };

  const revokeSession = async (session: SessionView) => {
    try {
      await api(`/api/v1/auth/sessions/${session.id}`, { method: "DELETE" });
      setActiveSessions((items) => items.filter((item) => item.id !== session.id));
      if (session.is_current) {
        router.push(loginPath);
      } else {
        showToast("Сеанс завершён");
      }
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось завершить сеанс",
        "error",
      );
    }
  };

  const revokeAll = async () => {
    if (!window.confirm("Завершить все сеансы, включая текущий?")) return;
    try {
      await api("/api/v1/auth/sessions/revoke-all", { method: "POST" });
      router.push(loginPath);
      router.refresh();
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось завершить сеансы",
        "error",
      );
    }
  };

  const beginMfa = async () => {
    setMfaBusy(true);
    try {
      const setup = await api<{ secret: string; otpauth_url: string }>("/api/v1/auth/mfa/setup", {
        method: "POST",
      });
      setMfaSetup(setup);
      setMfaCode("");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось начать настройку 2FA",
        "error",
      );
    } finally {
      setMfaBusy(false);
    }
  };

  const confirmMfa = async () => {
    if (mfaCode.trim().length < 6) {
      showToast("Введите шестизначный код из приложения", "error");
      return;
    }
    setMfaBusy(true);
    try {
      await api("/api/v1/auth/mfa/confirm", {
        method: "POST",
        body: { code: mfaCode.trim() },
      });
      setMfaEnabled(true);
      setMfaSetup(null);
      setMfaCode("");
      await refresh();
      showToast("Двухфакторная аутентификация включена", "success");
      router.refresh();
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Неверный код подтверждения",
        "error",
      );
    } finally {
      setMfaBusy(false);
    }
  };

  const disableMfa = async () => {
    if (mfaCode.trim().length < 6) {
      showToast("Введите текущий код из приложения", "error");
      return;
    }
    setMfaBusy(true);
    try {
      await api("/api/v1/auth/mfa/disable", {
        method: "POST",
        body: { code: mfaCode.trim() },
      });
      setMfaEnabled(false);
      setMfaCode("");
      await refresh();
      showToast("Двухфакторная аутентификация отключена");
      router.refresh();
    } catch (err) {
      showToast(err instanceof ClientApiError ? err.message : "Не удалось отключить 2FA", "error");
    } finally {
      setMfaBusy(false);
    }
  };

  const unblock = async (item: BlockedUser) => {
    try {
      await api(`/api/v1/blocked-users/${item.id}`, { method: "DELETE" });
      setBlockedUsers((items) => items.filter((entry) => entry.id !== item.id));
      showToast("Блокировка снята");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось снять блокировку",
        "error",
      );
    }
  };

  const exportData = async () => {
    setExporting(true);
    try {
      const response = await fetch("/api/v1/account/export", {
        credentials: "include",
        cache: "no-store",
      });
      if (!response.ok) throw new Error("export_failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "zooffer-account.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      showToast("Архив данных скачан", "success");
    } catch {
      showToast("Не удалось скачать архив данных", "error");
    } finally {
      setExporting(false);
    }
  };

  const deleteAccount = async () => {
    if (confirmation.trim().toUpperCase() !== "УДАЛИТЬ") {
      showToast("Введите слово УДАЛИТЬ для подтверждения", "error");
      return;
    }
    if (
      !window.confirm(
        "Аккаунт будет деактивирован, объявления сняты, контакты удалены. Это действие нельзя отменить.",
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      await api("/api/v1/account", {
        method: "DELETE",
        body: { confirmation: confirmation.trim() },
      });
      router.push(afterDeletePath);
      router.refresh();
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось удалить аккаунт",
        "error",
      );
      setDeleting(false);
    }
  };

  return (
    <div className="settings-stack">
      <section className="settings-card">
        <div className="card-head">
          <div>
            <h2>Публичное имя и город</h2>
            <p>Другие пользователи видят только имя, фамилию (если указана) и город.</p>
          </div>
        </div>
        <div className="field-row">
          <div className="field">
            <label htmlFor="settings-first-name">Имя *</label>
            <input
              id="settings-first-name"
              className="input"
              value={profile.firstName}
              onChange={(event) => setProfile({ ...profile, firstName: event.target.value })}
              maxLength={60}
            />
          </div>
          <div className="field">
            <label htmlFor="settings-last-name">Фамилия</label>
            <input
              id="settings-last-name"
              className="input"
              value={profile.lastName}
              onChange={(event) => setProfile({ ...profile, lastName: event.target.value })}
              maxLength={60}
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="settings-city">Город</label>
          <select
            id="settings-city"
            className="select"
            value={profile.cityId}
            onChange={(event) => setProfile({ ...profile, cityId: event.target.value })}
          >
            <option value="">Не указывать</option>
            {dictionaries?.cities.map((city) => (
              <option key={city.id} value={city.id}>
                {city.name}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => void saveProfile()}
          disabled={savingProfile}
        >
          <CheckIcon width={15} height={15} /> {savingProfile ? "Сохраняем…" : "Сохранить профиль"}
        </button>
      </section>

      <section className="settings-card">
        <div className="card-head">
          <div>
            <h2>Уведомления</h2>
            <p>Выберите, где получать каждый тип событий. В приложении — всегда.</p>
          </div>
        </div>
        <div className="pref-table" role="table" aria-label="Каналы уведомлений">
          <div className="pref-row pref-head" role="row">
            <span role="columnheader">Событие</span>
            <span role="columnheader">В приложении</span>
            <span role="columnheader">Telegram</span>
            <span role="columnheader">E-mail</span>
          </div>
          {prefs.map((item) => (
            <div className="pref-row" role="row" key={item.category}>
              <span role="cell">{categoryLabels[item.category] ?? item.category}</span>
              {(["in_app", "telegram", "email"] as const).map((channel) => (
                <label className="switch" role="cell" key={channel}>
                  <input
                    type="checkbox"
                    checked={item[channel] as boolean}
                    onChange={() => togglePref(item.category, channel)}
                    aria-label={`${categoryLabels[item.category] ?? item.category}: ${channel}`}
                  />
                  <span aria-hidden="true" />
                </label>
              ))}
            </div>
          ))}
        </div>
        <p className="field-hint">
          E-mail доставляется только после настройки почтового провайдера. Тихие часы настраиваются
          в боте и Mini App.
        </p>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => void savePreferences()}
          disabled={savingPrefs}
        >
          {savingPrefs ? "Сохраняем…" : "Сохранить настройки"}
        </button>
      </section>

      <section className="settings-card" id="mfa">
        <div className="card-head">
          <div>
            <h2>Двухфакторная аутентификация</h2>
            <p>Дополнительная защита входа. Обязательна для сотрудников Zooffer.</p>
          </div>
          <ShieldIcon width={22} height={22} />
        </div>
        {mfaEnabled ? (
          <div className="mfa-box">
            <p className="notice compact-notice">
              <strong>2FA включена.</strong> При входе понадобится код из
              приложения-аутентификатора.
            </p>
            <div className="inline-field">
              <input
                className="input"
                value={mfaCode}
                onChange={(event) => setMfaCode(event.target.value)}
                placeholder="Текущий код"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={8}
              />
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void disableMfa()}
                disabled={mfaBusy}
              >
                {mfaBusy ? "Проверяем…" : "Отключить 2FA"}
              </button>
            </div>
            <p className="field-hint">
              Для отключения нужен свежий код. Если код уже использовался при входе, дождитесь
              следующего.
            </p>
          </div>
        ) : mfaSetup ? (
          <div className="mfa-box">
            <ol className="mfa-steps">
              <li>
                Откройте приложение-аутентификатор (например, Aegis или Google Authenticator).
              </li>
              <li>
                Добавьте аккаунт вручную и введите секрет:
                <code className="mfa-secret">{mfaSetup.secret}</code>
              </li>
              <li>Введите шестизначный код из приложения ниже.</li>
            </ol>
            <p className="field-hint">
              Ссылка для настройки: <code className="mfa-uri">{mfaSetup.otpauth_url}</code>
            </p>
            <div className="inline-field">
              <input
                className="input"
                value={mfaCode}
                onChange={(event) => setMfaCode(event.target.value)}
                placeholder="Код из приложения"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={8}
              />
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => void confirmMfa()}
                disabled={mfaBusy}
              >
                {mfaBusy ? "Проверяем…" : "Включить 2FA"}
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  setMfaSetup(null);
                  setMfaCode("");
                }}
              >
                Отмена
              </button>
            </div>
          </div>
        ) : (
          <div className="mfa-box">
            <p className="muted">
              2FA пока не включена. Для панели модерации её нужно настроить заранее.
            </p>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => void beginMfa()}
              disabled={mfaBusy}
            >
              {mfaBusy ? "Готовим секрет…" : "Настроить 2FA"}
            </button>
          </div>
        )}
      </section>

      <section className="settings-card">
        <div className="card-head">
          <div>
            <h2>Активные сеансы</h2>
            <p>Устройства, с которых выполнен вход. Завершите всё, что не узнаёте.</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => void revokeAll()}>
            Завершить все
          </button>
        </div>
        <div className="session-list">
          {activeSessions.map((session) => (
            <div className="session-row" key={session.id}>
              <span className="grow">
                <strong>
                  {session.device_label || "Неизвестное устройство"}
                  {session.is_current && <span className="chip chip-live">Текущий</span>}
                </strong>
                <small>Последняя активность: {formatDateTime(session.last_seen_at)}</small>
                {session.user_agent && <small>{session.user_agent}</small>}
              </span>
              {!session.is_current && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void revokeSession(session)}
                >
                  Завершить
                </button>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="settings-card">
        <div className="card-head">
          <div>
            <h2>Заблокированные пользователи</h2>
            <p>Они не могут писать вам, а их объявления не показываются в подборе.</p>
          </div>
        </div>
        {blockedUsers.length === 0 ? (
          <p className="muted">Вы никого не блокировали.</p>
        ) : (
          <div className="session-list">
            {blockedUsers.map((item) => (
              <div className="session-row" key={item.id}>
                <span className="grow">
                  <strong>{item.display_name ?? "Владелец"}</strong>
                  <small>Заблокирован {formatDateTime(item.blocked_at)}</small>
                </span>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void unblock(item)}
                >
                  Снять блокировку
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="settings-card">
        <div className="card-head">
          <div>
            <h2>Что видят другие</h2>
            <p>Технически разделённые публичные и приватные данные.</p>
          </div>
          <ShieldIcon width={22} height={22} />
        </div>
        <div className="privacy-columns">
          <div>
            <strong>Публично</strong>
            <ul className="check-list">
              <li>Имя и, если указана, фамилия</li>
              <li>Город и регион без точного адреса</li>
              <li>Данные животного и фотографии объявления</li>
            </ul>
          </div>
          <div>
            <strong>Только вам</strong>
            <ul className="check-list muted">
              <li>E-mail, телефон и Telegram</li>
              <li>История свайпов, лимиты и подписка</li>
              <li>Документы животного и настройки</li>
            </ul>
          </div>
        </div>
        <div className="privacy-note">
          <ShieldIcon width={18} height={18} />
          <span>
            Статус прочтения сообщений не показывается другим пользователям, фото профиля
            отсутствует, а контакты не передаются автоматически.
          </span>
        </div>
      </section>

      <section className="settings-card danger-zone">
        <div className="card-head">
          <div>
            <h2>Данные и аккаунт</h2>
            <p>Скачайте архив или удалите аккаунт. Удаление необратимо.</p>
          </div>
        </div>
        <div className="btn-row">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => void exportData()}
            disabled={exporting}
          >
            <DocumentIcon width={15} height={15} />
            {exporting ? "Формируем архив…" : "Скачать мои данные"}
          </button>
          <Link href={supportPath} className="btn btn-ghost btn-sm">
            Написать в поддержку
          </Link>
        </div>
        <div className="delete-account">
          <label htmlFor="delete-confirmation">
            Для удаления введите <strong>УДАЛИТЬ</strong>
          </label>
          <div className="inline-field">
            <input
              id="delete-confirmation"
              className="input"
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              autoComplete="off"
            />
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={() => void deleteAccount()}
              disabled={deleting}
            >
              {deleting ? "Удаляем…" : "Удалить аккаунт"}
            </button>
          </div>
          <p className="field-hint">
            Объявления и анкеты будут сняты. Платёжные документы, которые закон требует хранить,
            останутся у платёжного провайдера без публичных данных.
          </p>
        </div>
      </section>
    </div>
  );
}
