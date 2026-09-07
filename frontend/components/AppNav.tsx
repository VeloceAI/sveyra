"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/api";
import {
  clearSession,
  getRefreshToken,
} from "@/lib/auth/session";

const LINKS = [
  { href: "/profile", label: "Profile" },
  { href: "/avatar", label: "Avatar" },
  { href: "/human-engine", label: "Human Engine" },
  { href: "/wardrobe", label: "Wardrobe" },
  { href: "/recommend", label: "Recommend" },
  { href: "/gaps", label: "Gaps" },
  { href: "/outfits", label: "Outfits" },
  { href: "/calendar", label: "Calendar" },
];

export function AppNav() {
  const router = useRouter();

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
      {process.env.NODE_ENV === "development" ? (
        <span className="dev-badge">Local dev</span>
      ) : (
        <button
          type="button"
          className="secondary"
          onClick={async () => {
            const refreshToken = getRefreshToken();
            if (refreshToken) await logout(refreshToken).catch(() => undefined);
            clearSession();
            router.replace("/login");
          }}
        >
          Log out
        </button>
      )}
    </header>
  );
}
