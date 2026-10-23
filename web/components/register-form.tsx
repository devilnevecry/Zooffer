"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { api, ClientApiError } from "@/lib/client";
import { safeNext } from "@/lib/navigation";
import type { AuthResponse, Dictionaries } from "@/lib/types";

export function RegisterForm({ dictionaries }: { dictionaries: Dictionaries | null }) {
  const router = useRouter();
  const params = useSearchParams();
  const { setSession } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    firstName: "",
    lastName: "",
    email: "",
    password: "",
    cityId: "",
    acceptedTerms: false,
    acceptedPrivacy: false,
    marketing: false,
  });
  const next = safeNext(params.get("next"), "/onboarding");
  const invite = params.get("invite") ?? params.get("ref") ?? "";

  const update = (key: keyof typeof form, value: string | boolean) =>
    setForm((current) => ({ ...current, [key]: value }));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (form.password.length < 10) {
      setError("Пароль должен содержать не менее 10 символов.");
      return;
    }
    if (!form.acceptedTerms || !form.acceptedPrivacy) {
      setError("Подтвердите согласие с документами, чтобы продолжить.");
      return;
    }
    setBusy(true);
    try {
      const payload = await api<AuthResponse>("/api/v1/auth/register", {
        method: "POST",
        body: {
          email: form.email,
          password: form.password,
          first_name: form.firstName,
          last_name: form.lastName.trim() || null,
          city_id: form.cityId ? Number(form.cityId) : null,
          accepted_terms: form.acceptedTerms,
          accepted_privacy: form.acceptedPrivacy,
          marketing_opt_in: form.marketing,
          invite_code: invite || null,
        },
      });
      setSession(payload);
      router.replace(next);
      router.refresh();
    } catch (err) {
      if (err instanceof ClientApiError) {
        setError(err.message);
      } else {
        setError("Не удалось создать аккаунт. Попробуйте ещё раз.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <div className="field-row">
        <div className="field">
          <label htmlFor="register-first">Имя</label>
          <input
            id="register-first"
            className="input"
            value={form.firstName}
            onChange={(event) => update("firstName", event.target.value)}
            autoComplete="given-name"
            maxLength={40}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="register-last">Фамилия — по желанию</label>
          <input
            id="register-last"
            className="input"
            value={form.lastName}
            onChange={(event) => update("lastName", event.target.value)}
            autoComplete="family-name"
            maxLength={40}
          />
        </div>
      </div>
      <p className="field-hint">
        Именно так вас увидят другие пользователи. Почта и контакты останутся
        скрытыми.
      </p>
      <div className="field">
        <label htmlFor="register-email">Почта</label>
        <input
          id="register-email"
          className="input"
          type="email"
          value={form.email}
          onChange={(event) => update("email", event.target.value)}
          autoComplete="email"
          inputMode="email"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="register-password">Пароль</label>
        <input
          id="register-password"
          className="input"
          type="password"
          value={form.password}
          onChange={(event) => update("password", event.target.value)}
          autoComplete="new-password"
          minLength={10}
          required
        />
        <span className="field-hint">Не меньше 10 символов.</span>
      </div>
      <div className="field">
        <label htmlFor="register-city">Город — по желанию</label>
        <select
          id="register-city"
          className="select"
          value={form.cityId}
          onChange={(event) => update("cityId", event.target.value)}
        >
          <option value="">Выберите позже</option>
          {dictionaries?.cities.map((city) => (
            <option key={city.id} value={city.id}>
              {city.name}
            </option>
          ))}
        </select>
      </div>
      <label className="check">
        <input
          type="checkbox"
          checked={form.acceptedTerms}
          onChange={(event) => update("acceptedTerms", event.target.checked)}
        />
        <span>
          Принимаю{" "}
          <Link href="/legal/terms" target="_blank">
            пользовательское соглашение
          </Link>{" "}
          и{" "}
          <Link href="/legal/rules" target="_blank">
            правила размещения
          </Link>
          .
        </span>
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={form.acceptedPrivacy}
          onChange={(event) => update("acceptedPrivacy", event.target.checked)}
        />
        <span>
          Даю{" "}
          <Link href="/legal/personal-data" target="_blank">
            согласие на обработку персональных данных
          </Link>{" "}
          и принимаю{" "}
          <Link href="/legal/privacy" target="_blank">
            политику конфиденциальности
          </Link>
          .
        </span>
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={form.marketing}
          onChange={(event) => update("marketing", event.target.checked)}
        />
        <span>Хочу получать редкие письма о новых функциях Zooffer.</span>
      </label>
      <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
        {busy ? "Создаём аккаунт…" : "Создать аккаунт"}
      </button>
    </form>
  );
}
