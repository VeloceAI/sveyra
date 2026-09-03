"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { login } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import { setSession, userIdFromAccessToken } from "@/lib/auth/session";
import { ErrorBanner } from "@/components/ErrorBanner";
import { sanitizeLoginRedirect } from "./sanitize-login-redirect";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await login(email.trim(), password);
      const userId = userIdFromAccessToken(token.access_token);
      if (!userId) throw new Error("Login succeeded but token subject was missing.");
      setSession(token.access_token, userId);
      router.replace(sanitizeLoginRedirect(params.get("next")));
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="card auth-card stack">
        <h1>Log in</h1>
        <p>Use your SVEYRA account to manage wardrobe and recommendations.</p>
        <ErrorBanner message={error} />
        <form className="stack" onSubmit={onSubmit}>
          <label>
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              required
              minLength={8}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p>
          No account? <Link href="/register">Register</Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="empty">Loading…</p>}>
      <LoginForm />
    </Suspense>
  );
}
