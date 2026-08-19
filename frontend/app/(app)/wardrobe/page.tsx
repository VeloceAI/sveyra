"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listWardrobe } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { WardrobeItem } from "@/lib/api/types";
import { ErrorBanner } from "@/components/ErrorBanner";

export default function WardrobeListPage() {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listWardrobe()
      .then((res) => {
        setItems(res.wardrobe_items);
        setTotal(res.total);
      })
      .catch((err) => setError(formatApiError(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Wardrobe</h1>
        <Link className="button" href="/wardrobe/new">
          Add item
        </Link>
      </div>
      <ErrorBanner message={error} />
      {loading ? <p className="empty">Loading…</p> : null}
      {!loading && items.length === 0 ? (
        <p className="empty">No wardrobe items yet. Add your first garment.</p>
      ) : null}
      <ul className="list card">
        {items.map((item) => (
          <li key={item.id}>
            <Link href={`/wardrobe/${item.id}`}>
              <strong>
                {item.category} · {item.color}
              </strong>
            </Link>
            <div>
              {item.brand} · <span className="mono">{item.id}</span>
            </div>
          </li>
        ))}
      </ul>
      {!loading ? <p className="empty">Total: {total}</p> : null}
    </div>
  );
}
