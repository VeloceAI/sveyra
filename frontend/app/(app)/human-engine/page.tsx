"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AvatarViewer from "@/components/AvatarViewer";
import { ErrorBanner } from "@/components/ErrorBanner";
import { buildHumanEnginePreview, fetchMediaObjectUrl } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type {
  CanonicalAvatarResponse,
  HumanEnginePreviewRequest,
} from "@/lib/api/types";

type MeasurementKey = Exclude<keyof HumanEnginePreviewRequest, "height_cm">;
type Control = {
  key: MeasurementKey;
  label: string;
  group: "Torso" | "Limbs" | "Head";
  neutralFraction: number;
  min: number;
  max: number;
};

const CONTROLS: readonly Control[] = [
  { key: "shoulder_width_cm", label: "Shoulders", group: "Torso", neutralFraction: 0.245, min: 0.75, max: 1.35 },
  { key: "chest_width_cm", label: "Chest width", group: "Torso", neutralFraction: 0.19, min: 0.7, max: 1.45 },
  { key: "chest_depth_cm", label: "Chest depth", group: "Torso", neutralFraction: 0.115, min: 0.7, max: 1.45 },
  { key: "waist_width_cm", label: "Waist width", group: "Torso", neutralFraction: 0.16, min: 0.65, max: 1.55 },
  { key: "waist_depth_cm", label: "Waist depth", group: "Torso", neutralFraction: 0.105, min: 0.65, max: 1.55 },
  { key: "hip_width_cm", label: "Hip width", group: "Torso", neutralFraction: 0.195, min: 0.7, max: 1.45 },
  { key: "hip_depth_cm", label: "Hip depth", group: "Torso", neutralFraction: 0.125, min: 0.7, max: 1.45 },
  { key: "upper_arm_radius_cm", label: "Upper arm", group: "Limbs", neutralFraction: 0.035, min: 0.65, max: 1.55 },
  { key: "forearm_radius_cm", label: "Forearm", group: "Limbs", neutralFraction: 0.027, min: 0.65, max: 1.55 },
  { key: "thigh_width_cm", label: "Thigh width", group: "Limbs", neutralFraction: 0.098, min: 0.65, max: 1.55 },
  { key: "calf_width_cm", label: "Calf width", group: "Limbs", neutralFraction: 0.068, min: 0.65, max: 1.55 },
  { key: "head_width_cm", label: "Head width", group: "Head", neutralFraction: 0.092, min: 0.8, max: 1.25 },
  { key: "head_depth_cm", label: "Head depth", group: "Head", neutralFraction: 0.115, min: 0.8, max: 1.25 },
] as const;

const INITIAL_RATIOS = Object.fromEntries(
  CONTROLS.map((control) => [control.key, 1]),
) as Record<MeasurementKey, number>;

function measurementPayload(
  height: number,
  ratios: Record<MeasurementKey, number>,
): HumanEnginePreviewRequest {
  const measurements = Object.fromEntries(
    CONTROLS.map((control) => [
      control.key,
      Number((height * control.neutralFraction * ratios[control.key]).toFixed(3)),
    ]),
  ) as Omit<HumanEnginePreviewRequest, "height_cm">;
  return { height_cm: height, ...measurements };
}

export default function HumanEnginePage() {
  const [heightCm, setHeightCm] = useState(178);
  const [ratios, setRatios] = useState(INITIAL_RATIOS);
  const [result, setResult] = useState<CanonicalAvatarResponse | null>(null);
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);
  const payload = useMemo(() => measurementPayload(heightCm, ratios), [heightCm, ratios]);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const built = await buildHumanEnginePreview(payload);
      const nextUrl = await fetchMediaObjectUrl(built.asset_id);
      setModelUrl((current) => {
        if (current) URL.revokeObjectURL(current);
        return nextUrl;
      });
      setResult(built);
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void generate();
    // The shell mounts this page only after a local or user session is ready.
    // Rebuilding remains explicit after the first neutral preview.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function reset() {
    setRatios({ ...INITIAL_RATIOS });
    setHeightCm(178);
  }

  return (
    <section className="engine-studio">
      <header className="engine-hero">
        <div>
          <p className="eyebrow">SVEYRA LAB / MILESTONE 2</p>
          <h1>Human Engine</h1>
          <p>Inspect the fixed human topology, measurement deformation, and animation rig.</p>
        </div>
        <div className="engine-statuses">
          <span className="status-live"><i /> Engine online</span>
          <span>Topology v0.1</span>
          <span>Rig v0.1</span>
        </div>
      </header>

      <ErrorBanner message={error} />
      <div className="engine-workspace">
        <aside className="engine-controls">
          <div className="panel-heading">
            <div><span>01</span><h2>Body parameters</h2></div>
            <button type="button" className="text-button" onClick={reset}>Reset</button>
          </div>

          <label className="engine-height">
            <span>Standing height</span>
            <strong>{heightCm} cm</strong>
            <input type="range" min={145} max={210} value={heightCm} onChange={(event) => setHeightCm(Number(event.target.value))} />
          </label>

          {(["Torso", "Limbs", "Head"] as const).map((group) => (
            <div className="control-group" key={group}>
              <h3>{group}</h3>
              {CONTROLS.filter((control) => control.group === group).map((control) => (
                <label className="parameter-row" key={control.key}>
                  <span>{control.label}</span>
                  <output>{payload[control.key]?.toFixed(1)} cm</output>
                  <input
                    type="range"
                    min={control.min}
                    max={control.max}
                    step={0.01}
                    value={ratios[control.key]}
                    onChange={(event) => setRatios((current) => ({
                      ...current,
                      [control.key]: Number(event.target.value),
                    }))}
                  />
                </label>
              ))}
            </div>
          ))}

          <button type="button" className="engine-generate" disabled={busy} onClick={() => void generate()}>
            {busy ? "Generating fitted human…" : "Generate fitted human"}
          </button>
          <p className="control-note">Length fitting, face identity, skin, eyes, and hair remain separate evidence-gated stages.</p>
        </aside>

        <div className="engine-viewport-panel">
          <div className="viewport-titlebar">
            <div><span className="viewport-dot" /> REALTIME VIEWPORT</div>
            <span>{result ? result.stage.replaceAll("_", " ") : "waiting for build"}</span>
          </div>
          <AvatarViewer url={modelUrl} height={680} rigged studio />
        </div>
      </div>

      <EngineEvidence result={result} />
    </section>
  );
}

function EngineEvidence({ result }: { result: CanonicalAvatarResponse | null }) {
  return (
    <section className="engine-evidence">
      <div className="panel-heading">
        <div><span>02</span><h2>Build evidence</h2></div>
        <span className={result?.parameter_fitted ? "evidence-pass" : "evidence-pending"}>
          {result?.parameter_fitted ? "PARAMETERS FITTED" : "AWAITING BUILD"}
        </span>
      </div>
      <div className="evidence-grid">
        <article><small>Surface</small><strong>{result?.vertex_count.toLocaleString() ?? "13,380"}</strong><span>stable vertices</span></article>
        <article><small>Topology</small><strong>{result?.triangle_count.toLocaleString() ?? "26,756"}</strong><span>triangles</span></article>
        <article><small>Skeleton</small><strong>{result?.joint_count ?? "163"}</strong><span>weighted joints</span></article>
        <article><small>Identity</small><strong>{result?.identity_fitted ? "Fitted" : "Not fitted"}</strong><span>honest stage gate</span></article>
      </div>
      {result && (
        <div className="evidence-details">
          <div>
            <h3>Runtime contract</h3>
            <dl>
              <div><dt>Topology</dt><dd>{result.topology_id} / {result.topology_version}</dd></div>
              <div><dt>Rig</dt><dd>{result.rig_id} / {result.rig_version}</dd></div>
              <div><dt>Deformer</dt><dd>{result.deformation_method ?? "neutral scale only"}</dd></div>
              <div><dt>Height</dt><dd>{result.height_cm.toFixed(1)} cm</dd></div>
            </dl>
          </div>
          <div>
            <h3>Current limitations</h3>
            <ul>{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
          </div>
        </div>
      )}
    </section>
  );
}
