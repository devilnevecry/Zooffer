import type { Metadata, Viewport } from "next";
import Script from "next/script";
import type { ReactNode } from "react";

import { AuthProvider } from "@/components/auth-provider";
import { MiniAppRoot } from "@/components/miniapp/telegram";

export const metadata: Metadata = {
  title: { absolute: "Zooffer Mini App" },
  description: "Zooffer внутри Telegram: подбор, объявления и переписка.",
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: { index: false, follow: false },
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#f3f6fa",
};

export default function MiniAppLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider initialUser={null} initialCsrf={null}>
      <Script
        src="https://telegram.org/js/telegram-web-app.js"
        strategy="afterInteractive"
      />
      <MiniAppRoot>{children}</MiniAppRoot>
    </AuthProvider>
  );
}
