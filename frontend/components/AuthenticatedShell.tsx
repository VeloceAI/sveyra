"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createDevelopmentSession } from "@/lib/api";
import { AppNav } from "@/components/AppNav";
import {
  getAccessToken,
  setSession,
  userIdFromAccessToken,
} from "@/lib/auth/session";

export function AuthenticatedShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (getAccessToken()) {
      setReady(true);
      return;
    }
    if (process.env.NODE_ENV === "development") {
      void createDevelopmentSession()
        .then((tokens) => {
          const userId = userIdFromAccessToken(tokens.access_token);
          if (!userId) throw new Error("Development token has no user id");
          setSession(tokens.access_token, userId, tokens.refresh_token);
          setReady(true);
        })
        .catch(() => router.replace(`/login?next=${encodeURIComponent(pathname)}`));
      return;
    }
    router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [pathname, router]);

  if (!ready) {
    return <main><p className="empty">Starting local development session…</p></main>;
  }
  return <><AppNav /><main>{children}</main></>;
}
