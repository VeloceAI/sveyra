"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { getAppearanceProfile, saveAppearanceProfile } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import {
  ApiError,
  AppearanceProfile,
  AppearanceProfileRequest,
  ContrastLevel,
  FaceShape,
  HairTexture,
  MakeupFinish,
  MakeupIntensity,
} from "@/lib/api/types";
import { Choice, DEPTHS, FOCUS, INITIAL, title, UNDERTONES } from "./appearance-options";

export default function AppearancePage() {
  const [form, setForm] = useState<AppearanceProfileRequest>(INITIAL);
  const [profile, setProfile] = useState<AppearanceProfile | null>(null);
  const [avoid, setAvoid] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getAppearanceProfile()
      .then((saved) => {
        setProfile(saved);
        setForm(saved);
        setAvoid(saved.makeup.avoid.join(", "));
      })
      .catch((caught) => {
        if (!(caught instanceof ApiError) || caught.code !== "appearance_profile_not_found") {
          setError(formatApiError(caught));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const completion = useMemo(() => {
    const complete = [
      form.skin.depth,
      form.skin.undertone,
      form.face.shape !== "unspecified" ? form.face.shape : "",
      form.eyes.color.trim(),
      form.hair.color.trim(),
      form.hair.texture,
      form.colour_analysis.contrast,
      form.makeup.intensity,
    ].filter(Boolean).length;
    return Math.round((complete / 8) * 100);
  }, [form]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const payload: AppearanceProfileRequest = {
        ...form,
        eyes: { color: form.eyes.color.trim() },
        hair: { ...form.hair, color: form.hair.color.trim() },
        makeup: {
          ...form.makeup,
          avoid: avoid
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        },
        evidence: {
          source: "self_reported",
          user_confirmed: true,
          confidence: 1,
        },
      };
      const saved = await saveAppearanceProfile(payload);
      setForm(saved);
      setProfile(saved);
      setNotice("Your appearance profile and starter palette are updated.");
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setSaving(false);
    }
  }

  function toggleFocus(value: string) {
    setForm((current) => ({
      ...current,
      makeup: {
        ...current.makeup,
        focus: current.makeup.focus.includes(value)
          ? current.makeup.focus.filter((item) => item !== value)
          : [...current.makeup.focus, value],
      },
    }));
  }

  return (
    <div className="appearance-studio">
      <header className="appearance-hero">
        <div>
          <span className="eyebrow">PERSONAL MODEL / APPEARANCE</span>
          <h1>Color Studio</h1>
          <p>
            Build a confirmed colour and beauty profile for clothes, combinations,
            makeup, hair and your future digital human.
          </p>
        </div>
        <div className="appearance-completion" aria-label={completion + "% complete"}>
          <strong>{completion}%</strong>
          <span>profile complete</span>
        </div>
      </header>

      <div className="appearance-trust">
        <strong>You stay the authority.</strong>
        <span>
          These values are self-confirmed. Photo analysis will arrive as an editable
          estimate with confidence—not overwrite your choices.
        </span>
      </div>

      <ErrorBanner message={error} />
      {notice ? <div className="notice">{notice}</div> : null}
      {loading ? <p className="empty">Loading your colour profile…</p> : null}

      <div className="appearance-layout">
        <form className="appearance-form" onSubmit={onSave}>
          <section className="appearance-panel">
            <div className="appearance-section-heading">
              <span>01</span>
              <div>
                <h2>Skin</h2>
                <p>Use indirect daylight and match your neck rather than flushed areas.</p>
              </div>
            </div>

            <div className="tone-picker">
              <label>
                Representative tone
                <span className="tone-input">
                  <input
                    type="color"
                    value={form.skin.tone_hex}
                    onChange={(event) =>
                      setForm((current) => ({
                        ...current,
                        skin: { ...current.skin, tone_hex: event.target.value.toUpperCase() },
                      }))
                    }
                  />
                  <code>{form.skin.tone_hex}</code>
                </span>
              </label>
              <label className="appearance-check">
                <input
                  type="checkbox"
                  checked={form.skin.sensitive}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      skin: { ...current.skin, sensitive: event.target.checked },
                    }))
                  }
                />
                My skin is sensitive
              </label>
            </div>

            <fieldset className="appearance-fieldset">
              <legend>Skin depth</legend>
              <div className="skin-depth-grid">
                {DEPTHS.map((depth) => (
                  <button
                    type="button"
                    key={depth.value}
                    className="skin-depth"
                    aria-pressed={form.skin.depth === depth.value}
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        skin: {
                          ...current.skin,
                          depth: depth.value,
                          tone_hex: depth.sample,
                        },
                      }))
                    }
                  >
                    <i style={{ background: depth.sample }} />
                    <span>{depth.label}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <fieldset className="appearance-fieldset">
              <legend>Undertone</legend>
              <div className="undertone-grid">
                {UNDERTONES.map((tone) => (
                  <button
                    type="button"
                    key={tone.value}
                    className="undertone-card"
                    aria-pressed={form.skin.undertone === tone.value}
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        skin: { ...current.skin, undertone: tone.value },
                      }))
                    }
                  >
                    <strong>{tone.label}</strong>
                    <span>{tone.hint}</span>
                  </button>
                ))}
              </div>
            </fieldset>
          </section>

          <section className="appearance-panel">
            <div className="appearance-section-heading">
              <span>02</span>
              <div>
                <h2>Features</h2>
                <p>These guide colour balance, makeup placement and future identity capture.</p>
              </div>
            </div>
            <div className="appearance-input-grid">
              <label>
                Face shape
                <select
                  value={form.face.shape}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      face: { shape: event.target.value as FaceShape },
                    }))
                  }
                >
                  {["unspecified", "oval", "round", "square", "heart", "oblong", "diamond"].map(
                    (shape) => (
                      <option key={shape} value={shape}>
                        {title(shape)}
                      </option>
                    ),
                  )}
                </select>
              </label>
              <label>
                Eye colour
                <input
                  value={form.eyes.color}
                  maxLength={40}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      eyes: { color: event.target.value },
                    }))
                  }
                />
              </label>
              <label>
                Hair colour
                <input
                  value={form.hair.color}
                  maxLength={40}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      hair: { ...current.hair, color: event.target.value },
                    }))
                  }
                />
              </label>
              <label>
                Hair texture
                <select
                  value={form.hair.texture}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      hair: { ...current.hair, texture: event.target.value as HairTexture },
                    }))
                  }
                >
                  {["straight", "wavy", "curly", "coily", "protective", "shaved"].map(
                    (texture) => (
                      <option key={texture} value={texture}>
                        {title(texture)}
                      </option>
                    ),
                  )}
                </select>
              </label>
            </div>
            <label className="appearance-check">
              <input
                type="checkbox"
                checked={form.hair.chemically_treated}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    hair: { ...current.hair, chemically_treated: event.target.checked },
                  }))
                }
              />
              My hair is coloured, relaxed, permed or otherwise chemically treated
            </label>

            <fieldset className="appearance-fieldset">
              <legend>Natural feature contrast</legend>
              <div className="choice-row">
                {(["low", "medium", "high"] as ContrastLevel[]).map((value) => (
                  <Choice
                    key={value}
                    value={value}
                    current={form.colour_analysis.contrast}
                    label={title(value)}
                    onSelect={(contrast) =>
                      setForm((current) => ({
                        ...current,
                        colour_analysis: { contrast },
                      }))
                    }
                  />
                ))}
              </div>
            </fieldset>
          </section>

          <section className="appearance-panel">
            <div className="appearance-section-heading">
              <span>03</span>
              <div>
                <h2>Makeup preferences</h2>
                <p>Guidance should follow your taste and routine, not prescribe a face.</p>
              </div>
            </div>
            <fieldset className="appearance-fieldset">
              <legend>Intensity</legend>
              <div className="choice-row">
                {(["none", "natural", "polished", "statement"] as MakeupIntensity[]).map(
                  (value) => (
                    <Choice
                      key={value}
                      value={value}
                      current={form.makeup.intensity}
                      label={title(value)}
                      onSelect={(intensity) =>
                        setForm((current) => ({
                          ...current,
                          makeup: { ...current.makeup, intensity },
                        }))
                      }
                    />
                  ),
                )}
              </div>
            </fieldset>
            <fieldset className="appearance-fieldset">
              <legend>Preferred finish</legend>
              <div className="choice-row">
                {(["natural", "matte", "dewy", "satin"] as MakeupFinish[]).map((value) => (
                  <Choice
                    key={value}
                    value={value}
                    current={form.makeup.finish}
                    label={title(value)}
                    onSelect={(finish) =>
                      setForm((current) => ({
                        ...current,
                        makeup: { ...current.makeup, finish },
                      }))
                    }
                  />
                ))}
              </div>
            </fieldset>
            <fieldset className="appearance-fieldset">
              <legend>Features you like to emphasize</legend>
              <div className="focus-row">
                {FOCUS.map((value) => (
                  <label key={value}>
                    <input
                      type="checkbox"
                      checked={form.makeup.focus.includes(value)}
                      onChange={() => toggleFocus(value)}
                    />
                    {title(value)}
                  </label>
                ))}
              </div>
            </fieldset>
            <label>
              Avoid or sensitivities
              <input
                value={avoid}
                maxLength={300}
                placeholder="heavy fragrance, glitter, matte lips"
                onChange={(event) => setAvoid(event.target.value)}
              />
              <span className="field-hint">Separate multiple preferences with commas.</span>
            </label>
          </section>

          <button className="appearance-save" type="submit" disabled={saving}>
            {saving ? "Building your palette…" : profile ? "Update my palette" : "Create my palette"}
          </button>
        </form>

        <aside className="palette-panel">
          {profile ? (
            <>
              <div className="palette-heading">
                <span className="eyebrow">YOUR STARTER PALETTE</span>
                <h2>{profile.palette.title}</h2>
                <p>{profile.palette.summary}</p>
              </div>

              <h3>Best colours</h3>
              <div className="palette-swatches">
                {profile.palette.best_colours.map((swatch) => (
                  <div key={swatch.hex}>
                    <i style={{ background: swatch.hex }} />
                    <span>{swatch.name}</span>
                  </div>
                ))}
              </div>

              <h3>Core neutrals</h3>
              <div className="neutral-swatches">
                {profile.palette.neutrals.map((swatch) => (
                  <div key={swatch.hex}>
                    <i style={{ background: swatch.hex }} />
                    <span>{swatch.name}</span>
                  </div>
                ))}
              </div>

              <h3>Combinations</h3>
              <div className="combination-list">
                {profile.palette.combinations.map((combination) => (
                  <article key={combination.name}>
                    <div className="combination-colours">
                      {combination.colours.map((colour) => (
                        <i key={colour.hex} style={{ background: colour.hex }} />
                      ))}
                    </div>
                    <strong>{combination.name}</strong>
                    <p>{combination.guidance}</p>
                  </article>
                ))}
              </div>

              <h3>Makeup direction</h3>
              <dl className="makeup-guidance">
                {Object.entries(profile.palette.makeup).map(([key, value]) => (
                  <div key={key}>
                    <dt>{title(key)}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>

              <div className="metal-line">
                <span>Metals</span>
                <strong>{profile.palette.metals.join(" · ")}</strong>
              </div>
            </>
          ) : (
            <div className="palette-empty">
              <div
                className="palette-orbit"
                style={{ "--tone": form.skin.tone_hex } as React.CSSProperties}
              />
              <span className="eyebrow">READY WHEN YOU ARE</span>
              <h2>Your palette will live here.</h2>
              <p>
                Confirm your appearance inputs to generate clothing colours, combinations,
                metals and makeup direction.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
