"use client";

import { useState } from "react";

import { useToast } from "./toast-provider";

import { ArrowIcon } from "./icons";

export function ShareButton({ title, url }: { title: string; url?: string }) {
  const showToast = useToast();
  const [busy, setBusy] = useState(false);

  const share = async () => {
    const link = url ?? window.location.href;
    setBusy(true);
    try {
      if (navigator.share) {
        await navigator.share({ title, text: `${title} — Zooffer`, url: link });
      } else {
        await navigator.clipboard.writeText(link);
        showToast("Ссылка скопирована");
      }
    } catch {
      // Sharing was cancelled or the clipboard is unavailable; no error toast needed.
    } finally {
      setBusy(false);
    }
  };

  return (
    <button type="button" className="btn btn-ghost" onClick={share} disabled={busy}>
      Поделиться <ArrowIcon width={16} height={16} />
    </button>
  );
}
