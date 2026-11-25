"use client";

import { useState } from "react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof document === "undefined") return "light";
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  });

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("zooffer-theme", next);
    } catch {
      // ignore
    }
    setTheme(next);
  };

  return (
    <button type="button" onClick={toggle} aria-label="Переключить тему" className="theme-toggle">
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
