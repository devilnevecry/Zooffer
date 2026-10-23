import type { ReactNode } from "react";

import { AuthProvider } from "@/components/auth-provider";
import { OfflineNotice } from "@/components/offline-notice";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { TabBar } from "@/components/tab-bar";
import { getMe } from "@/lib/api";

export default async function SiteLayout({ children }: { children: ReactNode }) {
  const me = await getMe();

  return (
    <AuthProvider initialUser={me?.user ?? null} initialCsrf={me?.csrf_token ?? null}>
      <a href="#main-content" className="skip-link">
        Перейти к содержанию
      </a>
      <OfflineNotice />
      <SiteHeader />
      <main id="main-content">{children}</main>
      <SiteFooter />
      <TabBar />
    </AuthProvider>
  );
}
