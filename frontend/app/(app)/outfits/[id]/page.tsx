"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { getOutfit } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { Outfit } from "@/lib/api/types";
import { ErrorBanner } from "@/components/ErrorBanner";

export default function OutfitDetailPage() {
  const params = useParams<{ id: string }>();
  const [outfit, setOutfit] = useState<Outfit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!params.id) return;
    getOutfit(params.id)
      .then(setOutfit)
      .catch((err) => setError(formatApiError(err)))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) return <p className="empty">Loading outfit…</p>;

  if (!outfit) {
    return (
      <div className="stack">
        <ErrorBanner message={error ?? "Outfit not found."} />
        <Link href="/outfits">Back</Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Outfit</h1>
        <Link href="/outfits">Back</Link>
      </div>
      <ErrorBanner message={error} />
      <section className="card stack">
        <div>
          <strong>Occasion:</strong> {outfit.occasion}
        </div>
        <div className="mono">{outfit.id}</div>
        <div>
          <strong>Items</strong>
          <ul className="list">
            {outfit.item_ids.map((id) => (
              <li key={id}>
                <Link className="mono" href={`/wardrobe/${id}`}>
                  {id}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <strong>Rationale</strong>
          <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(outfit.rationale, null, 2)}
          </pre>
        </div>
      </section>
    </div>
  );
}
