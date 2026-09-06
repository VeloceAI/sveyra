"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import {
  deleteWearLog,
  getWardrobeUsage,
  listCalendar,
  listWardrobe,
  logWear,
} from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { WardrobeUsageResponse, WearLog, WardrobeItem } from "@/lib/api/types";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function describe(item: WardrobeItem) {
  return [item.color, item.category].filter(Boolean).join(" ");
}

export default function CalendarPage() {
  const [entries, setEntries] = useState<WearLog[]>([]);
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [usage, setUsage] = useState<WardrobeUsageResponse | null>(null);
  const [wornOn, setWornOn] = useState(today());
  const [selected, setSelected] = useState<string[]>([]);
  const [occasion, setOccasion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [calendar, wardrobe, stats] = await Promise.all([
        listCalendar(),
        listWardrobe(),
        getWardrobeUsage(),
      ]);
      setEntries(calendar.entries);
      setItems(wardrobe.wardrobe_items);
      setUsage(stats);
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await logWear({
        worn_on: wornOn,
        item_ids: selected,
        occasion: occasion.trim() || null,
        // A date in the future is a plan, not a record. Deciding here rather
        // than asking keeps the form to one question.
        planned: wornOn > today(),
      });
      setSelected([]);
      setOccasion("");
      await load();
    } catch (caught) {
      setError(formatApiError(caught));
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(day: string) {
    setError(null);
    try {
      await deleteWearLog(day);
      await load();
    } catch (caught) {
      setError(formatApiError(caught));
    }
  }

  const nameFor = (id: string) => {
    const match = items.find((item) => item.id === id);
    return match ? describe(match) : "an item no longer in your wardrobe";
  };

  const neverWorn = (usage?.never_worn_item_ids ?? [])
    .map((id) => items.find((item) => item.id === id))
    .filter((item): item is WardrobeItem => Boolean(item));

  return (
    <section>
      <h1>Style calendar</h1>
      <p className="muted">
        Log what you wore, or plan a day ahead. Over time this is what shows which
        clothes earn their place.
      </p>

      <ErrorBanner message={error} />

      <form onSubmit={onSave} className="calendar-form">
        <label>
          Date
          <input
            type="date"
            value={wornOn}
            onChange={(event) => setWornOn(event.target.value)}
            required
          />
        </label>
        <label>
          Occasion
          <input
            value={occasion}
            onChange={(event) => setOccasion(event.target.value)}
            placeholder="work, dinner, weekend"
            maxLength={100}
          />
        </label>

        <fieldset className="calendar-items">
          <legend>What you wore</legend>
          {items.length === 0 ? (
            <p className="muted">Add wardrobe items first and they will appear here.</p>
          ) : (
            items.map((item) => (
              <label key={item.id} className="checkbox">
                <input
                  type="checkbox"
                  checked={selected.includes(item.id)}
                  onChange={(event) =>
                    setSelected((current) =>
                      event.target.checked
                        ? [...current, item.id]
                        : current.filter((id) => id !== item.id),
                    )
                  }
                />
                {describe(item)}
              </label>
            ))
          )}
        </fieldset>

        <button type="submit" disabled={saving}>
          {saving ? "Saving…" : wornOn > today() ? "Plan this day" : "Log this day"}
        </button>
      </form>

      <h2>Recent days</h2>
      {loading && <p className="muted">Loading…</p>}
      {!loading && entries.length === 0 && (
        <p className="muted">Nothing logged yet. Start with today.</p>
      )}
      <ul className="calendar-list">
        {entries.map((entry) => (
          <li key={entry.id}>
            <div>
              <strong>{entry.worn_on}</strong>
              {entry.planned && <span className="tag"> planned</span>}
              {entry.occasion && <span className="muted"> · {entry.occasion}</span>}
              <div className="muted">
                {entry.item_ids.length > 0
                  ? entry.item_ids.map(nameFor).join(", ")
                  : "No items recorded"}
              </div>
            </div>
            <button type="button" className="secondary" onClick={() => void onDelete(entry.worn_on)}>
              Remove
            </button>
          </li>
        ))}
      </ul>

      {usage && usage.logged_days > 0 && (
        <div className="usage">
          <h2>What you actually wear</h2>
          <p className="muted">Across {usage.logged_days} logged days.</p>
          {usage.most_worn.length > 0 && (
            <ul>
              {usage.most_worn.map((stat) => (
                <li key={stat.item_id}>
                  {nameFor(stat.item_id)} — worn {stat.times_worn}{" "}
                  {stat.times_worn === 1 ? "time" : "times"}
                </li>
              ))}
            </ul>
          )}
          {neverWorn.length > 0 && (
            <>
              <h3>Never worn</h3>
              <p className="muted">
                {neverWorn.length} item{neverWorn.length === 1 ? "" : "s"} you own but have
                not logged.
              </p>
              <ul>
                {neverWorn.map((item) => (
                  <li key={item.id}>{describe(item)}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
