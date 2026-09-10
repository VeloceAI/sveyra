"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { getPlatformReadiness } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { CapabilityStatus, PlatformReadiness } from "@/lib/api/types";

const STATUS_LABEL: Record<CapabilityStatus, string> = {
  ready: "Working",
  demo: "Demo adapter",
  setup_required: "Needs setup",
  planned: "Planned",
};

const FLOW = [
  { number: "01", label: "Capture", detail: "Your style, closet, and body" },
  { number: "02", label: "Understand", detail: "Garment and color evidence" },
  { number: "03", label: "Style", detail: "Rank complete owned looks" },
  { number: "04", label: "Preview", detail: "Avatar and visual try-on" },
  { number: "05", label: "Learn", detail: "Save, wear, edit, and reject" },
] as const;

export default function TodayPage() {
  const [readiness, setReadiness] = useState<PlatformReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPlatformReadiness()
      .then(setReadiness)
      .catch((caught) => setError(formatApiError(caught)));
  }, []);

  const date = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date());

  return (
    <section className="today-studio">
      <header className="today-hero">
        <div>
          <p className="today-kicker">YOUR PERSONAL STYLE SYSTEM</p>
          <p className="today-date">{date}</p>
          <h1>Make your closet<br />work <span>harder.</span></h1>
          <p className="today-intro">
            Start with a useful daily wardrobe. Every save, swap, and wear makes
            the next recommendation more personal.
          </p>
        </div>
        <ProgressDial percent={readiness?.personal_model.core_completion_percent ?? 0} />
      </header>

      <ErrorBanner message={error} />
      {!readiness && !error ? <p className="today-loading">Reading your closet…</p> : null}

      {readiness ? (
        <>
          <section className="today-action">
            <div className="today-action-index">NEXT</div>
            <div>
              <p>{readiness.parity_phase}</p>
              <h2>{readiness.personal_model.next_action.label}</h2>
              <span>{readiness.personal_model.next_action.reason}</span>
            </div>
            <Link className="today-action-link" href={readiness.personal_model.next_action.href}>
              Continue <span aria-hidden="true">→</span>
            </Link>
          </section>

          <section className="today-snapshot" aria-labelledby="snapshot-heading">
            <div className="today-section-heading">
              <div>
                <p>PERSONAL MODEL</p>
                <h2 id="snapshot-heading">What SVEYRA knows</h2>
              </div>
              <span>Evidence, not guesses</span>
            </div>
            <div className="snapshot-grid">
              <SnapshotStat
                label="Style direction"
                value={readiness.personal_model.style_ready ? "Ready" : "Not set"}
                ready={readiness.personal_model.style_ready}
              />
              <SnapshotStat
                label="Owned garments"
                value={String(readiness.personal_model.wardrobe_items)}
                ready={readiness.personal_model.wardrobe_items > 0}
              />
              <SnapshotStat
                label="Identified garments"
                value={`${readiness.personal_model.enriched_items}/${readiness.personal_model.wardrobe_items}`}
                ready={
                  readiness.personal_model.wardrobe_items > 0
                  && readiness.personal_model.enriched_items === readiness.personal_model.wardrobe_items
                }
              />
              <SnapshotStat
                label="Body measurements"
                value={String(readiness.personal_model.body_measurement_count)}
                ready={readiness.personal_model.body_ready}
              />
              <SnapshotStat
                label="Color profile"
                value={readiness.personal_model.appearance_ready ? "Ready" : "Optional"}
                ready={readiness.personal_model.appearance_ready}
              />
            </div>
          </section>

          <section className="today-flow" aria-labelledby="flow-heading">
            <div className="today-section-heading">
              <div>
                <p>ONE CONNECTED LOOP</p>
                <h2 id="flow-heading">How a look is made</h2>
              </div>
              <span>{readiness.product_message}</span>
            </div>
            <ol>
              {FLOW.map((step) => (
                <li key={step.number}>
                  <span>{step.number}</span>
                  <strong>{step.label}</strong>
                  <p>{step.detail}</p>
                </li>
              ))}
            </ol>
          </section>

          <section className="today-capabilities" aria-labelledby="capability-heading">
            <div className="today-section-heading">
              <div>
                <p>ENGINE ROOM</p>
                <h2 id="capability-heading">What works today</h2>
              </div>
              <span>Provider truth is visible by design</span>
            </div>
            <div className="capability-grid">
              {readiness.capabilities.map((capability) => (
                <article className="capability-card" key={capability.key}>
                  <div className="capability-topline">
                    <span className={`capability-status is-${capability.status}`}>
                      {STATUS_LABEL[capability.status]}
                    </span>
                    <small>{capability.provider}</small>
                  </div>
                  <h3>{capability.label}</h3>
                  <p>{capability.summary}</p>
                  {capability.limitation ? <em>{capability.limitation}</em> : null}
                  {capability.href ? <Link href={capability.href}>Open feature →</Link> : null}
                </article>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </section>
  );
}

function ProgressDial({ percent }: { percent: number }) {
  return (
    <div
      className="today-progress"
      style={{ "--progress": `${percent * 3.6}deg` } as React.CSSProperties}
      aria-label={`Core setup ${percent}% complete`}
    >
      <div>
        <strong>{percent}%</strong>
        <span>core setup</span>
      </div>
    </div>
  );
}

function SnapshotStat({
  label,
  value,
  ready,
}: {
  label: string;
  value: string;
  ready: boolean;
}) {
  return (
    <article>
      <span className={ready ? "snapshot-dot is-ready" : "snapshot-dot"} />
      <small>{label}</small>
      <strong>{value}</strong>
    </article>
  );
}
