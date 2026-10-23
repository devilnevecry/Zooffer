import { redirect } from "next/navigation";

import { getMe } from "./api";
import type { MeResponse } from "./types";

export async function requireMe(nextPath = "/account"): Promise<MeResponse> {
  const me = await getMe();
  if (!me) {
    redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  }
  return me;
}
