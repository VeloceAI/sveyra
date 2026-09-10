"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { MediaPreview } from "@/components/MediaPreview";
import { listWardrobe } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { WardrobeItem } from "@/lib/api/types";
import { getRememberedMediaAsset } from "@/lib/auth/session";

export default function WardrobeListPage() {
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listWardrobe()
      .then((response) => setItems(response.wardrobe_items))
      .catch((caught) => setError(formatApiError(caught)))
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(
    () => ["all", ...Array.from(new Set(items.map((item) => item.category))).sort()],
    [items],
  );
  const visible = filter === "all" ? items : items.filter((item) => item.category === filter);
  const identified = items.filter((item) => (
    typeof item.attributes.cv === "object" && item.attributes.cv !== null
  )).length;

  return (
    <section className="closet-page">
      <header className="closet-hero">
        <div>
          <p className="closet-kicker">YOUR DIGITAL CLOSET</p>
          <h1>Everything you<br />can wear.</h1>
        </div>
        <div className="closet-hero-side">
          <p>{items.length} owned · {identified} identified</p>
          <Link className="closet-add" href="/wardrobe/new">Add photos <span>+</span></Link>
        </div>
      </header>

      <ErrorBanner message={error} />
      {loading ? <p className="empty">Opening your closet…</p> : null}

      {!loading && items.length === 0 ? (
        <section className="closet-empty">
          <p>YOUR CLOSET IS READY FOR ITS FIRST PIECE</p>
          <h2>Start with what you wear most.</h2>
          <span>Photograph a few reliable tops, bottoms, shoes, and one layer.</span>
          <Link href="/wardrobe/new">Choose garment photos →</Link>
        </section>
      ) : null}

      {items.length > 0 ? (
        <>
          <nav className="closet-filters" aria-label="Filter closet by category">
            {categories.map((category) => (
              <button
                type="button"
                key={category}
                className={filter === category ? "is-active" : ""}
                onClick={() => setFilter(category)}
              >
                {category}
              </button>
            ))}
          </nav>
          <div className="closet-grid">
            {visible.map((item) => {
              const assetId = item.media_asset_ids[0] ?? getRememberedMediaAsset(item.id);
              const identifiedItem = typeof item.attributes.cv === "object" && item.attributes.cv !== null;
              return (
                <article className="closet-card" key={item.id}>
                  <Link href={`/wardrobe/${item.id}`} className="closet-card-image">
                    <MediaPreview assetId={assetId} alt={`${item.color} ${item.category}`} />
                  </Link>
                  <div className="closet-card-meta">
                    <span className={identifiedItem ? "is-identified" : ""}>
                      {identifiedItem ? "Identified" : "Needs review"}
                    </span>
                    <Link href={`/wardrobe/${item.id}`}>
                      <strong>{item.color} {item.category}</strong>
                      <small>{item.brand}</small>
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      ) : null}
    </section>
  );
}
