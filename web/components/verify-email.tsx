"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, ClientApiError } from "@/lib/client";

export function VerifyEmail() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"loading" | "done" | "error">(token ? "loading" : "error");
  const [message, setMessage] = useState(token ? "" : "В ссылке нет токена подтверждения.");
  const started = useRef(false);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    api("/api/v1/auth/email/verify", { method: "POST", body: { token } })
      .then(() => {
        setState("done");
        setMessage("Почта подтверждена. Спасибо!");
      })
      .catch((err) => {
        setState("error");
        setMessage(
          err instanceof ClientApiError ? err.message : "Ссылка недействительна или устарела.",
        );
      });
  }, [token]);

  if (state === "loading") {
    return (
      <div className="empty-state card-padded">
        <h2>Проверяем ссылку…</h2>
        <div className="loading-line" style={{ width: "70%" }} />
      </div>
    );
  }

  return (
    <div className="empty-state card-padded">
      <h2>{state === "done" ? "Готово" : "Не получилось"}</h2>
      <p>{message}</p>
      <Link href={state === "done" ? "/account" : "/support"} className="btn btn-primary">
        {state === "done" ? "Перейти в аккаунт" : "Написать в поддержку"}
      </Link>
    </div>
  );
}
