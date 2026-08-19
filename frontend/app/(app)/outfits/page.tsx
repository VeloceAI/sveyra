"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listOutfits } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { Outfit } from "@/lib/api/types";
import { ErrorBanner } from "@/components/ErrorBanner";

export default function OutfitsPage() {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listOutfits()
      .then((res) => {
        setOutfits(res.outfits);
        setTotal(res.total);
      })
      .catch((err) => setError(formatApiError(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Saved outfits</h1>
        <Link href="/recommend">Get recommendations</Link>
      </div>
      <ErrorBanner message={error} />
      {loading ? <p className="empty">Loading…</p> : null}
      {!loading && outfits.length === 0 ? (
        <p className="empty">No saved outfits yet.</p>
      ) : null}
      <ul className="list card">
        {outfits.map((outfit) => (
          <li key={outfit.id}>
            <Link href={`/outfits/${outfit.id}`}>
              <strong>{outfit.occasion}</strong>
            </Link>
            <div className="mono">{outfit.id}</div>
            <div>{outfit.item_ids.length} item(s)</div>
          </li>
        ))}
      </ul>
      {!loading ? <p className="empty">Total: {total}</p> : null}
    </div>
  );
}
