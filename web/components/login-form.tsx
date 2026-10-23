"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "./auth-provider";
import { api, ClientApiError } from "@/lib/client";
import { safeNext } from "@/lib/navigation";
import type { AuthResponse } from "@/lib/types";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { setSession } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfa, setMfa] = useState("");
  const [showMfa, setShowMfa] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const next = safeNext(params.get("next"));

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = await api<AuthResponse>("/api/v1/auth/login", {
        method: "POST",
        body: {
          email,
          password,
          mfa_code: showMfa && mfa ? mfa : null,
        },
      });
      setSession(payload);
      router.replace(next);
      router.refresh();
    } catch (err) {
      if (err instanceof ClientApiError) {
        if (err.code === "mfa_required") setShowMfa(true);
        setError(err.message);
      } else {
        setError("Не удалось войти. Попробуйте ещё раз.");
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
      <div className="field">
        <label htmlFor="login-email">Почта</label>
        <input
          id="login-email"
          className="input"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          autoComplete="email"
          inputMode="email"
          required
        />
      </div>
      <div className="field">
        <label htmlFor="login-password">Пароль</label>
        <input
          id="login-password"
          className="input"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
          required
        />
      </div>
      {showMfa && (
        <div className="field">
          <label htmlFor="login-mfa">Код двухфакторной защиты</label>
          <input
            id="login-mfa"
            className="input"
            inputMode="numeric"
            value={mfa}
            onChange={(event) => setMfa(event.target.value)}
            autoComplete="one-time-code"
            placeholder="6 цифр"
          />
        </div>
      )}
      <div className="form-row-between">
        <Link href="/forgot-password" className="text-link">
          Забыли пароль?
        </Link>
      </div>
      <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
        {busy ? "Входим…" : "Войти"}
      </button>
    </form>
  );
}
