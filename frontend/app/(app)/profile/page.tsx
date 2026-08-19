"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  createBodyProfile,
  getCurrentProfile,
  listBodyProfiles,
  saveProfile,
} from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { BodyProfile, PersistedProfile } from "@/lib/api/types";
import { getUserId } from "@/lib/auth/session";
import { ErrorBanner } from "@/components/ErrorBanner";

function parseJsonObject(raw: string, label: string): Record<string, unknown> {
  const trimmed = raw.trim();
  if (!trimmed) return {};
  try {
    const value = JSON.parse(trimmed) as unknown;
    if (value === null || typeof value !== "object" || Array.isArray(value)) {
      throw new Error(`${label} must be a JSON object`);
    }
    return value as Record<string, unknown>;
  } catch (err) {
    if (err instanceof Error) throw err;
    throw new Error(`${label} must be valid JSON`);
  }
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<PersistedProfile | null>(null);
  const [bodies, setBodies] = useState<BodyProfile[]>([]);
  const [preferences, setPreferences] = useState('{"style":"minimal"}');
  const [dislikes, setDislikes] = useState("{}");
  const [budget, setBudget] = useState('{"currency":"USD","max":200}');
  const [measurements, setMeasurements] = useState("{}");
  const [fitPreferences, setFitPreferences] = useState('{"ease":"regular"}');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  async function reload() {
    setError(null);
    const userId = getUserId();
    if (!userId) {
      setError("Session user id missing. Please log in again.");
      setLoading(false);
      return;
    }
    try {
      const current = await getCurrentProfile();
      setProfile(current);
      setPreferences(JSON.stringify(current.preferences ?? {}, null, 2));
      setDislikes(JSON.stringify(current.dislikes ?? {}, null, 2));
      setBudget(JSON.stringify(current.budget ?? {}, null, 2));
    } catch (err) {
      const message = formatApiError(err);
      if (!message.includes("profile_not_found")) {
        setError(message);
      } else {
        setProfile(null);
        setNotice("No style profile yet. Save one below.");
      }
    }
    try {
      const listed = await listBodyProfiles(userId);
      setBodies(listed.body_profiles);
    } catch (err) {
      const message = formatApiError(err);
      if (!message.includes("body_profile_not_found")) {
        setError((prev) => prev ?? message);
      } else {
        setBodies([]);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function onSaveStyle(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = await saveProfile({
        preferences: parseJsonObject(preferences, "preferences"),
        dislikes: parseJsonObject(dislikes, "dislikes"),
        budget: parseJsonObject(budget, "budget"),
      });
      setProfile(saved);
      setNotice("Style profile saved.");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  async function onSaveBody(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    const userId = getUserId();
    if (!userId) {
      setError("Session user id missing.");
      setSaving(false);
      return;
    }
    try {
      await createBodyProfile(userId, {
        measurements: parseJsonObject(measurements, "measurements"),
        fit_preferences: parseJsonObject(fitPreferences, "fit_preferences"),
      });
      setNotice("Body/fit profile saved.");
      const listed = await listBodyProfiles(userId);
      setBodies(listed.body_profiles);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="empty">Loading profile…</p>;

  return (
    <div className="stack">
      <h1>Profile</h1>
      <ErrorBanner message={error} />
      {notice ? <div className="notice">{notice}</div> : null}

      <section className="card stack">
        <h2>Style profile</h2>
        {profile ? (
          <p className="mono">
            user {profile.user_id} · style {profile.style_profile_id}
          </p>
        ) : (
          <p className="empty">Not created yet.</p>
        )}
        <form className="stack" onSubmit={onSaveStyle}>
          <label>
            preferences (JSON)
            <textarea rows={4} value={preferences} onChange={(e) => setPreferences(e.target.value)} />
          </label>
          <label>
            dislikes (JSON)
            <textarea rows={3} value={dislikes} onChange={(e) => setDislikes(e.target.value)} />
          </label>
          <label>
            budget (JSON)
            <textarea rows={3} value={budget} onChange={(e) => setBudget(e.target.value)} />
          </label>
          <button type="submit" disabled={saving}>
            Save style profile
          </button>
        </form>
      </section>

      <section className="card stack">
        <h2>Body / fit profile</h2>
        <form className="stack" onSubmit={onSaveBody}>
          <label>
            measurements (JSON)
            <textarea
              rows={3}
              value={measurements}
              onChange={(e) => setMeasurements(e.target.value)}
            />
          </label>
          <label>
            fit_preferences (JSON)
            <textarea
              rows={3}
              value={fitPreferences}
              onChange={(e) => setFitPreferences(e.target.value)}
            />
          </label>
          <button type="submit" disabled={saving}>
            Add body profile
          </button>
        </form>
        {bodies.length === 0 ? (
          <p className="empty">No body profiles yet.</p>
        ) : (
          <ul className="list">
            {bodies.map((body) => (
              <li key={body.id}>
                <div className="mono">{body.id}</div>
                <div>fit: {JSON.stringify(body.fit_preferences)}</div>
                <div>measurements: {JSON.stringify(body.measurements)}</div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
