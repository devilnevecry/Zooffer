"use client";

import { useState } from "react";

import { CheckIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api, ClientApiError } from "@/lib/client";

const categories = [
  { value: "food", label: "Корм" },
  { value: "stores", label: "Магазины" },
  { value: "vet", label: "Ветеринария" },
  { value: "grooming", label: "Груминг" },
  { value: "services", label: "Услуги" },
];

export function PartnerInquiryForm() {
  const showToast = useToast();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [form, setForm] = useState({
    company: "",
    contactName: "",
    telegram: "",
    category: "food",
    message: "",
    consent: false,
  });

  const update = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) =>
    setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.consent) {
      showToast("Подтвердите согласие на обработку данных", "error");
      return;
    }
    setBusy(true);
    try {
      await api("/api/v1/public/partner-inquiries", {
        method: "POST",
        body: {
          company: form.company.trim(),
          contact_name: form.contactName.trim(),
          telegram: form.telegram.trim(),
          category: form.category,
          message: form.message.trim(),
          consent: form.consent,
        },
      });
      setDone(true);
      showToast("Заявка отправлена", "success");
    } catch (err) {
      showToast(
        err instanceof ClientApiError ? err.message : "Не удалось отправить заявку",
        "error",
      );
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <div className="empty-state compact">
        <CheckIcon width={40} height={40} />
        <h2>Заявка получена</h2>
        <p>
          Мы ответим в Telegram на указанный контакт. Отправляя заявку, вы соглашаетесь на обработку
          данных для рассмотрения сотрудничества.
        </p>
      </div>
    );
  }

  return (
    <form className="form-card" onSubmit={submit}>
      <div className="field-row">
        <div className="field">
          <label htmlFor="partner-company">Компания *</label>
          <input
            id="partner-company"
            className="input"
            value={form.company}
            onChange={(event) => update("company", event.target.value)}
            minLength={2}
            maxLength={160}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="partner-contact">Контактное лицо *</label>
          <input
            id="partner-contact"
            className="input"
            value={form.contactName}
            onChange={(event) => update("contactName", event.target.value)}
            minLength={2}
            maxLength={120}
            required
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="partner-telegram">Telegram для связи *</label>
        <input
          id="partner-telegram"
          className="input"
          value={form.telegram}
          onChange={(event) => update("telegram", event.target.value)}
          placeholder="@username или https://t.me/username"
          maxLength={64}
          required
        />
        <p className="field-hint">Почта и телефон не запрашиваются — вся связь идёт в Telegram.</p>
      </div>
      <div className="field">
        <label htmlFor="partner-category">Категория *</label>
        <select
          id="partner-category"
          className="select"
          value={form.category}
          onChange={(event) => update("category", event.target.value)}
        >
          {categories.map((category) => (
            <option key={category.value} value={category.value}>
              {category.label}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="partner-message">О предложении *</label>
        <textarea
          id="partner-message"
          className="textarea"
          rows={5}
          minLength={10}
          maxLength={3000}
          value={form.message}
          onChange={(event) => update("message", event.target.value)}
          placeholder="Что вы предлагаете владельцам животных и какие условия готовы обсудить"
          required
        />
      </div>
      <label className="check">
        <input
          type="checkbox"
          checked={form.consent}
          onChange={(event) => update("consent", event.target.checked)}
          required
        />
        Согласен на обработку персональных данных для рассмотрения заявки.
      </label>
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? "Отправляем…" : "Отправить заявку"}
      </button>
    </form>
  );
}
