"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearSession, getAccessToken } from "@/lib/auth/session";

const LINKS = [
  { href: "/profile", label: "Profile" },
  { href: "/wardrobe", label: "Wardrobe" },
  { href: "/recommend", label: "Recommend" },
  { href: "/outfits", label: "Outfits" },
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
    return <p className="empty">Checking session…</p>;
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
        onClick={() => {
          clearSession();
          router.replace("/login");
        }}
      >
        Log out
      </button>
    </header>
  );
}
