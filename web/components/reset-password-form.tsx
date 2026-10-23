"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { api, ClientApiError } from "@/lib/client";

export function ResetPasswordForm() {
  const params = useSearchParams();
  const router = useRouter();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password.length < 10) {
      setError("Пароль должен содержать не менее 10 символов.");
      return;
    }
    if (password !== repeat) {
      setError("Пароли не совпадают.");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/auth/password/reset/confirm", {
        method: "POST",
        body: { token, new_password: password },
      });
      setDone(true);
      setTimeout(() => router.push("/login"), 1600);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Не удалось обновить пароль.");
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="form-error" role="alert">
        Ссылка неполная. Запросите новое письмо для сброса пароля.
      </div>
    );
  }

  if (done) {
    return (
      <div className="empty-state card-padded">
        <h2>Пароль обновлён</h2>
        <p>Сейчас перенаправим вас на страницу входа.</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit}>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <div className="field">
        <label htmlFor="reset-password">Новый пароль</label>
        <input
          id="reset-password"
          className="input"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          minLength={10}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="reset-repeat">Повторите пароль</label>
        <input
          id="reset-repeat"
          className="input"
          type="password"
          value={repeat}
          onChange={(event) => setRepeat(event.target.value)}
          autoComplete="new-password"
          required
        />
      </div>
      <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
        {busy ? "Сохраняем…" : "Сохранить пароль"}
      </button>
    </form>
  );
}
