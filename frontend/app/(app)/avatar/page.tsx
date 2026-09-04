"use client";

import { useState } from "react";
import AvatarViewer from "@/components/AvatarViewer";
import { ErrorBanner } from "@/components/ErrorBanner";
import { buildAvatar, fetchMediaObjectUrl } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { AvatarBuildResponse } from "@/lib/api/types";

const VIEWS = [
  { key: "front", label: "Front", required: true },
  { key: "side", label: "Side", required: false },
  { key: "back", label: "Back", required: false },
] as const;

type ViewKey = (typeof VIEWS)[number]["key"];

export default function AvatarPage() {
  const [files, setFiles] = useState<Partial<Record<ViewKey, File>>>({});
  const [heightCm, setHeightCm] = useState("178");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AvatarBuildResponse | null>(null);
  const [modelUrl, setModelUrl] = useState<string | null>(null);

  async function onBuild(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    const front = files.front;
    if (!front) {
      setError("A front photo is required: it is what the body is fitted from.");
      return;
    }
    const height = Number(heightCm);
    if (!Number.isFinite(height) || height < 50 || height > 260) {
      setError("Enter a height in centimetres between 50 and 260.");
      return;
    }

    setBusy(true);
    setModelUrl(null);
    try {
      const built = await buildAvatar(height, {
        front,
        side: files.side ?? null,
        back: files.back ?? null,
      });
      setResult(built);

      setModelUrl(await fetchMediaObjectUrl(built.asset_id));
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h1>Your avatar</h1>
      <p className="muted">
        Photograph yourself standing, head to toe, against a plain wall. A front photo is
        required; a side photo is what makes depth real rather than inferred.
      </p>

      <ErrorBanner message={error} />

      <form onSubmit={onBuild} className="avatar-form">
        <label>
          Height in centimetres
          <input
            type="number"
            min={50}
            max={260}
            value={heightCm}
            onChange={(event) => setHeightCm(event.target.value)}
            required
          />
        </label>

        <div className="avatar-uploads">
          {VIEWS.map((view) => (
            <label key={view.key}>
              {view.label}
              {view.required ? " (required)" : " (optional)"}
              <input
                type="file"
                accept="image/*"
                onChange={(event) =>
                  setFiles((current) => ({
                    ...current,
                    [view.key]: event.target.files?.[0],
                  }))
                }
              />
            </label>
          ))}
        </div>

        <button type="submit" disabled={busy}>
          {busy ? "Building…" : "Build my avatar"}
        </button>
      </form>

      <AvatarViewer url={modelUrl} />

      {result && (
        <div className="avatar-report">
          <h2>Measurements</h2>
          <table>
            <tbody>
              {Object.entries(result.measurements).map(([name, value]) => (
                <tr key={name}>
                  <td>{name.replace(/_/g, " ").replace(" cm", "")}</td>
                  <td className="numeric">{value.toFixed(1)} cm</td>
                </tr>
              ))}
            </tbody>
          </table>

          <p className="muted">
            Built from {result.source_views} view{result.source_views === 1 ? "" : "s"} in{" "}
            {Math.round(result.profiling_ms.total_ms ?? 0)} ms. Confidence{" "}
            {Math.round((result.confidence.overall ?? 0) * 100)}%.
          </p>

          {result.confidence.warnings.map((warning) => (
            <p key={warning} className="muted warning">
              {warning}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
