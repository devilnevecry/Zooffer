"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

type ToastTone = "default" | "error" | "success";

interface ToastState {
  message: string;
  tone: ToastTone;
  visible: boolean;
}

const ToastContext = createContext<((message: string, tone?: ToastTone) => void) | null>(
  null,
);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState>({
    message: "",
    tone: "default",
    visible: false,
  });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((message: string, tone: ToastTone = "default") => {
    if (timer.current) clearTimeout(timer.current);
    if (hideTimer.current) clearTimeout(hideTimer.current);
    setToast({ message, tone, visible: true });
    timer.current = setTimeout(() => {
      setToast((current) => ({ ...current, visible: false }));
    }, 3600);
  }, []);

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
      if (hideTimer.current) clearTimeout(hideTimer.current);
    },
    [],
  );

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div
        className="toast"
        data-visible={toast.visible}
        data-tone={toast.tone}
        role="status"
        aria-live="polite"
      >
        {toast.message}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const showToast = useContext(ToastContext);
  if (!showToast) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return showToast;
}
