"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { createOutfit, getRecommendations } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { RecommendationCandidate } from "@/lib/api/types";
import { ErrorBanner } from "@/components/ErrorBanner";

export default function RecommendPage() {
  const [occasion, setOccasion] = useState("casual");
  const [results, setResults] = useState<RecommendationCandidate[]>([]);
  const [resolvedOccasion, setResolvedOccasion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingIndex, setSavingIndex] = useState<number | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const response = await getRecommendations(occasion.trim());
      setResults(response.recommendations);
      setResolvedOccasion(response.occasion);
      if (response.recommendations.length === 0) {
        setNotice("No outfit combinations available for this wardrobe/occasion.");
      }
    } catch (err) {
      setResults([]);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  async function saveLook(candidate: RecommendationCandidate, index: number) {
    if (!resolvedOccasion) return;
    setSavingIndex(index);
    setError(null);
    setNotice(null);
    try {
      const outfit = await createOutfit({
        occasion: resolvedOccasion,
        item_ids: candidate.item_ids,
        rationale: { text: candidate.rationale, source: "recommendation" },
      });
      setNotice(`Saved outfit ${outfit.id}.`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSavingIndex(null);
    }
  }

  return (
    <div className="stack">
      <h1>Recommendations</h1>
      <p>Ask what to wear for an occasion using your owned wardrobe metadata.</p>
      <ErrorBanner message={error} />
      {notice ? <div className="notice">{notice}</div> : null}

      <form className="card stack" onSubmit={onSubmit}>
        <label>
          occasion
          <input
            required
            maxLength={100}
            value={occasion}
            onChange={(e) => setOccasion(e.target.value)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Ranking…" : "Get recommendations"}
        </button>
      </form>

      {results.length > 0 ? (
        <ul className="list card">
          {results.map((candidate, index) => (
            <li key={`${candidate.item_ids.join("-")}-${index}`} className="stack">
              <strong>Look {index + 1}</strong>
              <div>
                Items:{" "}
                {candidate.item_ids.map((id) => (
                  <span key={id}>
                    <Link className="mono" href={`/wardrobe/${id}`}>
                      {id}
                    </Link>{" "}
                  </span>
                ))}
              </div>
              <p>{candidate.rationale}</p>
              <button
                type="button"
                className="secondary"
                disabled={savingIndex === index}
                onClick={() => void saveLook(candidate, index)}
              >
                {savingIndex === index ? "Saving…" : "Save as outfit"}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <p>
        <Link href="/outfits">View saved outfits</Link>
      </p>
    </div>
  );
}
