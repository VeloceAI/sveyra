"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { MediaPreview } from "@/components/MediaPreview";
import {
  createOutfit,
  getRecommendations,
  listWardrobe,
} from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { RecommendationCandidate, WardrobeItem } from "@/lib/api/types";

const OCCASIONS = ["Everyday", "Work", "Dinner", "Party", "Travel"];

function pieceName(item: WardrobeItem | undefined) {
  if (!item) return "Closet item";
  return `${item.color} ${item.category}`;
}

export default function RecommendPage() {
  const [occasion, setOccasion] = useState("Everyday");
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [lockedItemIds, setLockedItemIds] = useState<string[]>([]);
  const [results, setResults] = useState<RecommendationCandidate[]>([]);
  const [resolvedOccasion, setResolvedOccasion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loadingCloset, setLoadingCloset] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [savingIndex, setSavingIndex] = useState<number | null>(null);
  const [swappingKey, setSwappingKey] = useState<string | null>(null);

  const itemById = useMemo(
    () => new Map(items.map((item) => [item.id, item])),
    [items],
  );

  useEffect(() => {
    listWardrobe()
      .then((response) => {
        setItems(response.wardrobe_items);
        const requestedItemId = new URLSearchParams(window.location.search).get("item");
        if (!requestedItemId) return;
        if (response.wardrobe_items.some((item) => item.id === requestedItemId)) {
          setLockedItemIds([requestedItemId]);
        } else {
          setError("That closet item is no longer available.");
        }
      })
      .catch((caught) => setError(formatApiError(caught)))
      .finally(() => setLoadingCloset(false));
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const requestedOccasion = occasion.trim();
    if (!requestedOccasion) return;
    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const response = await getRecommendations(requestedOccasion, {
        required_item_ids: lockedItemIds,
      });
      setResults(response.recommendations);
      setResolvedOccasion(response.occasion);
      if (response.recommendations.length === 0) {
        setNotice(
          lockedItemIds.length > 0
            ? "Add a compatible top, bottom, dress, or shoe to complete a look around this piece."
            : "Add a few compatible pieces before generating a complete look.",
        );
      }
    } catch (caught) {
      setResults([]);
      setError(formatApiError(caught));
    } finally {
      setGenerating(false);
    }
  }

  async function swapPiece(
    candidate: RecommendationCandidate,
    lookIndex: number,
    itemId: string,
  ) {
    const activeOccasion = resolvedOccasion ?? occasion.trim();
    const key = `${lookIndex}:${itemId}`;
    setSwappingKey(key);
    setError(null);
    setNotice(null);
    try {
      const response = await getRecommendations(activeOccasion, {
        required_item_ids: candidate.item_ids.filter((id) => id !== itemId),
        replacement_item_id: itemId,
      });
      const replacement = response.recommendations[0];
      if (!replacement) {
        setNotice(
          `No other ${itemById.get(itemId)?.category ?? "garment"} is available for this look.`,
        );
        return;
      }
      setResults((current) => current.map((look, index) => (
        index === lookIndex ? replacement : look
      )));
      setNotice("One piece changed. The rest of the look stayed fixed.");
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setSwappingKey(null);
    }
  }

  async function saveLook(candidate: RecommendationCandidate, index: number) {
    if (!resolvedOccasion) return;
    setSavingIndex(index);
    setError(null);
    setNotice(null);
    try {
      await createOutfit({
        occasion: resolvedOccasion,
        item_ids: candidate.item_ids,
        rationale: { text: candidate.rationale, source: "recommendation" },
      });
      setNotice(`Look ${index + 1} is saved to Looks.`);
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setSavingIndex(null);
    }
  }

  const lockedItems = lockedItemIds
    .map((itemId) => itemById.get(itemId))
    .filter((item): item is WardrobeItem => Boolean(item));

  return (
    <section className="stylist-page">
      <header className="stylist-hero">
        <p className="stylist-kicker">YOUR PERSONAL STYLIST</p>
        <h1>What are we<br />dressing for?</h1>
        <p className="stylist-intro">
          Build complete looks from pieces you already own. Lock one favorite,
          then swap any unlocked slot without losing the rest.
        </p>
      </header>

      <ErrorBanner message={error} />
      {notice ? <div className="notice stylist-notice">{notice}</div> : null}

      <form className="stylist-prompt" onSubmit={onSubmit}>
        <label htmlFor="occasion">Tell SVEYRA where you are going</label>
        <div className="stylist-input-row">
          <input
            id="occasion"
            required
            maxLength={100}
            value={occasion}
            onChange={(event) => setOccasion(event.target.value)}
            placeholder="A rooftop dinner on a warm evening"
          />
          <button type="submit" disabled={generating || loadingCloset || items.length === 0}>
            {generating ? "Building looks..." : "Create looks"}
          </button>
        </div>
        <div className="stylist-occasion-list" aria-label="Quick occasions">
          {OCCASIONS.map((option) => (
            <button
              type="button"
              key={option}
              className={occasion === option ? "is-active" : ""}
              onClick={() => setOccasion(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </form>

      {loadingCloset ? <p className="empty">Opening your closet...</p> : null}
      {!loadingCloset && items.length === 0 ? (
        <section className="stylist-empty">
          <p>YOUR STYLIST NEEDS SOMETHING TO WORK WITH</p>
          <h2>Add the clothes you reach for first.</h2>
          <Link href="/wardrobe/new">Import garment photos</Link>
        </section>
      ) : null}

      {lockedItems.length > 0 ? (
        <aside className="stylist-lock">
          <div>
            <span>LOCKED PIECE</span>
            <strong>{pieceName(lockedItems[0])}</strong>
            <small>This piece will appear in every generated look.</small>
          </div>
          <button type="button" onClick={() => setLockedItemIds([])}>Remove lock</button>
        </aside>
      ) : null}

      {results.length > 0 ? (
        <section className="stylist-results">
          <header>
            <div>
              <p>{resolvedOccasion?.toUpperCase()}</p>
              <h2>{results.length} looks from your closet</h2>
            </div>
            <Link href="/outfits">Saved looks</Link>
          </header>

          <div className="stylist-look-list">
            {results.map((candidate, lookIndex) => (
              <article
                className="stylist-look"
                key={`${candidate.item_ids.join("-")}-${lookIndex}`}
              >
                <div className="stylist-look-number">
                  <span>LOOK</span>
                  <strong>{String(lookIndex + 1).padStart(2, "0")}</strong>
                </div>
                <div className="stylist-piece-grid">
                  {candidate.item_ids.map((itemId) => {
                    const item = itemById.get(itemId);
                    const isLocked = lockedItemIds.includes(itemId);
                    const mediaId = item?.media_asset_ids[0] ?? null;
                    const swapKey = `${lookIndex}:${itemId}`;
                    return (
                      <div className="stylist-piece" key={itemId}>
                        <Link
                          href={`/wardrobe/${itemId}`}
                          aria-label={`Open ${pieceName(item)}`}
                        >
                          <MediaPreview assetId={mediaId} alt={pieceName(item)} />
                        </Link>
                        <div className="stylist-piece-meta">
                          <div>
                            <strong>{pieceName(item)}</strong>
                            <small>{item?.brand ?? "Closet piece"}</small>
                          </div>
                          {isLocked ? (
                            <span>Locked</span>
                          ) : (
                            <button
                              type="button"
                              disabled={swappingKey !== null}
                              onClick={() => void swapPiece(candidate, lookIndex, itemId)}
                            >
                              {swappingKey === swapKey ? "Swapping..." : "Swap"}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="stylist-look-story">
                  <p>{candidate.rationale}</p>
                  <button
                    type="button"
                    disabled={savingIndex !== null}
                    onClick={() => void saveLook(candidate, lookIndex)}
                  >
                    {savingIndex === lookIndex ? "Saving..." : "Save this look"}
                  </button>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
