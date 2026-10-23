"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "./auth-provider";
import { HeartIcon } from "./icons";
import { useToast } from "./toast-provider";
import { api } from "@/lib/client";
import type { FavoriteList } from "@/lib/types";

export function FavoriteButton({ listingId }: { listingId: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const showToast = useToast();
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    api<FavoriteList>("/api/v1/favorites")
      .then((data) => {
        if (!cancelled) {
          setSaved(data.items.some((item) => item.public_id === listingId));
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [user, listingId]);

  const toggle = async () => {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(window.location.pathname)}`);
      return;
    }
    setBusy(true);
    try {
      if (saved) {
        await api(`/api/v1/favorites/${listingId}`, { method: "DELETE" });
        setSaved(false);
        showToast("Удалено из избранного");
      } else {
        await api(`/api/v1/favorites/${listingId}`, { method: "POST" });
        setSaved(true);
        showToast("Сохранено в избранное", "success");
      }
    } catch {
      showToast("Не удалось обновить избранное", "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      className={saved ? "btn btn-secondary is-saved" : "btn btn-secondary"}
      onClick={toggle}
      disabled={busy}
      aria-pressed={saved}
    >
      <HeartIcon fill={saved ? "currentColor" : "none"} />
      {saved ? "В избранном" : "В избранное"}
    </button>
  );
}
