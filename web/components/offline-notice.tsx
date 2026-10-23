"use client";

import { useEffect, useState } from "react";

export function OfflineNotice() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (!offline) return null;
  return (
    <div className="offline-banner" role="status" aria-live="polite">
      Нет подключения к интернету. Показанные данные могут быть устаревшими.
    </div>
  );
}
