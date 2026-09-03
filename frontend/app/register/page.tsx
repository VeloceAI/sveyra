"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { login, register } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import { setSession, userIdFromAccessToken } from "@/lib/auth/session";
import { ErrorBanner } from "@/components/ErrorBanner";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(email.trim(), password);
      const token = await login(email.trim(), password);
      const userId = userIdFromAccessToken(token.access_token);
      if (!userId) throw new Error("Registration succeeded but token subject was missing.");
      setSession(token.access_token, userId);
      router.replace("/profile");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-shell">
      <div className="card auth-card stack">
        <h1>Register</h1>
        <p>Create an account. Password must be at least 8 characters.</p>
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
              maxLength={72}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Creating…" : "Create account"}
          </button>
        </form>
        <p>
          Already registered? <Link href="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
