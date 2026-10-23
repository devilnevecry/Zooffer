"use client";

import { useState } from "react";

import { api, ClientApiError } from "@/lib/client";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ message: string }>("/api/v1/auth/password/reset/request", {
        method: "POST",
        body: { email },
      });
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof ClientApiError ? err.message : "Не удалось отправить запрос.");
    } finally {
      setBusy(false);
    }
  };

  if (message) {
    return (
      <div className="empty-state card-padded">
        <h2>Проверьте почту</h2>
        <p>{message}</p>
        <p className="muted">
          Письмо может прийти в течение нескольких минут. Проверьте папку «Спам».
        </p>
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
      <p className="modal-lead">
        Укажите почту, на которую зарегистрирован аккаунт. Мы отправим ссылку для
        сброса пароля.
      </p>
      <div className="field">
        <label htmlFor="forgot-email">Почта</label>
        <input
          id="forgot-email"
          className="input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          required
        />
      </div>
      <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
        {busy ? "Отправляем…" : "Отправить ссылку"}
      </button>
    </form>
  );
}
