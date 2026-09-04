"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { logout } from "@/lib/api";
import { clearSession, getAccessToken, getRefreshToken } from "@/lib/auth/session";

const LINKS = [
  { href: "/profile", label: "Profile" },
  { href: "/avatar", label: "Avatar" },
  { href: "/wardrobe", label: "Wardrobe" },
  { href: "/recommend", label: "Recommend" },
  { href: "/gaps", label: "Gaps" },
  { href: "/outfits", label: "Outfits" },
  { href: "/calendar", label: "Calendar" },
];

export function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setReady(true);
  }, [pathname, router]);

  if (!ready) {
    return <p className="empty">Checking sessionâ€¦</p>;
  }

  return (
    <header className="nav">
      <Link href="/wardrobe" className="nav-brand">
        SVEYRA
      </Link>
      <nav className="nav-links">
        {LINKS.map((link) => (
          <Link key={link.href} href={link.href}>
            {link.label}
          </Link>
        ))}
      </nav>
      <button
        type="button"
        className="secondary"
        onClick={async () => {
          const refreshToken = getRefreshToken();
          if (refreshToken) {
            await logout(refreshToken).catch(() => undefined);
          }
          clearSession();
          router.replace("/login");
        }}
      >
        Log out
      </button>
    </header>
  );
}
