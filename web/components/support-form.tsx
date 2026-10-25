"use client";

import Link from "next/link";
import { useState } from "react";

import { CheckIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";

export function SupportForm({
  authenticated,
  loginPath = "/login?next=%2Fsupport",
}: {
  authenticated: boolean;
  loginPath?: string;
}) {
  const showToast = useToast();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [consent, setConsent] = useState(false);

  if (!authenticated) {
    return (
      <div className="empty-state compact">
        <h2>Войдите, чтобы написать в поддержку</h2>
        <p>
          Так мы сможем ответить в вашем аккаунте и сохранить историю обращения. Для срочных
          вопросов о безопасности используйте форму после входа.
        </p>
        <Link href={loginPath} className="btn btn-primary">
          Войти в аккаунт
        </Link>
      </div>
    );
  }

  if (done) {
    return (
      <div className="empty-state compact">
        <CheckIcon width={40} height={40} />
        <h2>Обращение создано</h2>
        <p>
          Ответ появится в разделе уведомлений и в переписке поддержки. Мы не просим присылать
          пароли, коды из SMS или полные данные карты.
        </p>
      </div>
    );
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!consent) {
      showToast("Подтвердите согласие на обработку обращения", "error");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/support/tickets", {
        method: "POST",
        body: { subject: subject.trim(), message: message.trim(), consent },
      });
      setDone(true);
      showToast("Обращение отправлено", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось отправить обращение",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="form-card" onSubmit={submit}>
      <div className="field">
        <label htmlFor="support-subject">Тема *</label>
        <input
          id="support-subject"
          className="input"
          value={subject}
          onChange={(event) => setSubject(event.target.value)}
          minLength={3}
          maxLength={160}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="support-message">Опишите ситуацию *</label>
        <textarea
          id="support-message"
          className="textarea"
          rows={7}
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          minLength={10}
          maxLength={5000}
          placeholder="Что произошло, какое объявление или диалог затронут, чего вы ожидаете"
          required
        />
      </div>
      <label className="check">
        <input
          type="checkbox"
          checked={consent}
          onChange={(event) => setConsent(event.target.checked)}
          required
        />
        Согласен на обработку обращения и указанных в нём данных.
      </label>
      <p className="field-hint">
        Не отправляйте пароли, коды из SMS, полные номера карт и документы. Для проверки объявления
        достаточно ссылки или публичного ID.
      </p>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "Отправляем…" : "Отправить обращение"}
      </button>
    </form>
  );
}
