import type { Metadata, Viewport } from "next";
import "@fontsource/onest/400.css";
import "@fontsource/onest/500.css";
import "@fontsource/onest/600.css";
import "@fontsource/onest/700.css";
import "@fontsource/unbounded/500.css";
import "@fontsource/unbounded/600.css";

import { ToastProvider } from "@/components/toast-provider";
import "./globals.css";

const appUrl = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(appUrl),
  title: {
    default: "Zooffer — животные находят своих людей",
    template: "%s · Zooffer",
  },
  description:
    "Zooffer — бережный подбор животных: продажа, вязка, племенное разведение и пристройство. Живые объявления, взаимные совпадения и безопасная переписка.",
  applicationName: "Zooffer",
  openGraph: {
    type: "website",
    locale: "ru_RU",
    siteName: "Zooffer",
    title: "Zooffer — животные находят своих людей",
    description:
      "Подбор, объявления и переписка для тех, кто выбирает животное осознанно.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Zooffer — животные находят своих людей",
    description: "Бережный подбор животных и безопасная переписка.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#f3f6fa",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body>
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}
