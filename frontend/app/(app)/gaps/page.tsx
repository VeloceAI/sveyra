"use client";

import { useCallback, useEffect, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { getShoppingRecommendations, getWardrobeGaps } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { GapCategory, ShoppingProduct, WardrobeGap } from "@/lib/api/types";

const CATEGORY_LABEL: Record<GapCategory, string> = {
  top: "Tops",
  bottom: "Bottoms",
  shoes: "Shoes",
};

function money(value: number) {
  return value.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

export default function GapsPage() {
  const [gaps, setGaps] = useState<WardrobeGap[] | null>(null);
  const [products, setProducts] = useState<ShoppingProduct[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Gaps first: shopping only means anything once you know what is missing.
      const gapResponse = await getWardrobeGaps();
      setGaps(gapResponse.gaps);

      if (gapResponse.gaps.length === 0) {
        setProducts([]);
      } else {
        const shopping = await getShoppingRecommendations();
        setProducts(shopping.products);
      }
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const suggestionsFor = (category: GapCategory) =>
    products.filter((product) => product.category === category);

  return (
    <section>
      <h1>Wardrobe gaps</h1>
      <p className="muted">
        What your wardrobe cannot currently put together, and what would fill it.
      </p>

      <ErrorBanner message={error} />

      <button type="button" onClick={() => void load()} disabled={loading}>
        {loading ? "Checking…" : "Check again"}
      </button>

      {gaps !== null && gaps.length === 0 && !loading && (
        <div className="gap-clear">
          <h2>Nothing missing</h2>
          <p className="muted">
            Your wardrobe covers tops, bottoms and shoes, so it can build a complete
            outfit. Add more pieces any time to widen the options.
          </p>
        </div>
      )}

      {gaps !== null && gaps.length > 0 && (
        <>
          <p className="muted">
            {gaps.length} gap{gaps.length === 1 ? "" : "s"} found.
          </p>

          <div className="gap-list">
            {gaps.map((gap) => {
              const suggestions = suggestionsFor(gap.category);
              return (
                <article key={gap.category} className="gap-card">
                  <header>
                    <h2>{CATEGORY_LABEL[gap.category]}</h2>
                    <span className="gap-priority">{gap.priority} priority</span>
                  </header>
                  <p>{gap.reason}</p>

                  {suggestions.length > 0 ? (
                    <ul className="product-list">
                      {suggestions.map((product) => (
                        <li key={product.id}>
                          <div>
                            <strong>{product.name}</strong>
                            <span className="muted"> · {product.brand}</span>
                          </div>
                          <div className="product-meta">
                            <span className="numeric">{money(product.price)}</span>
                            <a href={product.url} target="_blank" rel="noreferrer noopener">
                              View
                            </a>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">No suggestions available for this gap yet.</p>
                  )}
                </article>
              );
            })}
          </div>

          {products.length > 0 && (
            <p className="muted warning">
              These are sample products from a placeholder catalogue, not a real
              storefront. Prices and links are illustrative.
            </p>
          )}
        </>
      )}
    </section>
  );
}
