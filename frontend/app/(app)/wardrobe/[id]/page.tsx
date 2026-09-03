"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  deleteWardrobeItem,
  enrichWardrobeItem,
  getWardrobeItem,
  patchWardrobeItem,
  uploadMedia,
} from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { WardrobeItem } from "@/lib/api/types";
import {
  forgetMediaAsset,
  getRememberedMediaAsset,
  rememberMediaAsset,
} from "@/lib/auth/session";
import { ErrorBanner } from "@/components/ErrorBanner";
import { MediaPreview } from "@/components/MediaPreview";

export default function WardrobeDetailPage() {
  const params = useParams<{ id: string }>();
  const itemId = params.id;
  const router = useRouter();
  const [item, setItem] = useState<WardrobeItem | null>(null);
  const [category, setCategory] = useState("");
  const [color, setColor] = useState("");
  const [brand, setBrand] = useState("");
  const [attributes, setAttributes] = useState("{}");
  const [assetId, setAssetId] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!itemId) return;
    setAssetId(getRememberedMediaAsset(itemId));
    getWardrobeItem(itemId)
      .then((res) => {
        setItem(res);
        setCategory(res.category);
        setColor(res.color);
        setBrand(res.brand);
        setAttributes(JSON.stringify(res.attributes ?? {}, null, 2));
      })
      .catch((err) => setError(formatApiError(err)))
      .finally(() => setLoading(false));
  }, [itemId]);

  async function onPatch(event: FormEvent) {
    event.preventDefault();
    if (!itemId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const parsed = JSON.parse(attributes) as unknown;
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("attributes must be a JSON object");
      }
      const updated = await patchWardrobeItem(itemId, {
        category: category.trim(),
        color: color.trim(),
        brand: brand.trim(),
        attributes: parsed as Record<string, unknown>,
      });
      setItem(updated);
      setNotice("Item updated.");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!itemId || !file) {
      setError("Choose an image file to upload.");
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const asset = await uploadMedia(file, itemId);
      rememberMediaAsset(itemId, asset.id);
      setAssetId(asset.id);
      setNotice("Media uploaded and linked to this item.");
      setFile(null);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function onEnrich() {
    if (!itemId) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await enrichWardrobeItem(itemId);
      setItem(updated);
      setCategory(updated.category);
      setColor(updated.color);
      setBrand(updated.brand);
      setAttributes(JSON.stringify(updated.attributes ?? {}, null, 2));
      setNotice("Enrichment complete.");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    if (!itemId) return;
    if (!window.confirm("Delete this wardrobe item and its linked media?")) return;
    setBusy(true);
    setError(null);
    try {
      await deleteWardrobeItem(itemId);
      forgetMediaAsset(itemId);
      router.replace("/wardrobe");
    } catch (err) {
      setError(formatApiError(err));
      setBusy(false);
    }
  }

  if (loading) return <p className="empty">Loading item…</p>;
  if (!item) {
    return (
      <div className="stack">
        <ErrorBanner message={error ?? "Item not found."} />
        <Link href="/wardrobe">Back to wardrobe</Link>
      </div>
    );
  }

  return (
    <div className="stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Wardrobe item</h1>
        <Link href="/wardrobe">Back</Link>
      </div>
      <p className="mono">{item.id}</p>
      <ErrorBanner message={error} />
      {notice ? <div className="notice">{notice}</div> : null}

      <section className="card stack">
        <h2>Media</h2>
        <MediaPreview assetId={assetId} />
        <form className="stack" onSubmit={onUpload}>
          <label>
            Upload garment image
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <button type="submit" disabled={busy || !file}>
            Upload &amp; link
          </button>
        </form>
        <button type="button" className="secondary" disabled={busy} onClick={() => void onEnrich()}>
          Run garment enrichment
        </button>
      </section>

      <form className="card stack" onSubmit={onPatch}>
        <h2>Edit metadata</h2>
        <label>
          category
          <input required value={category} onChange={(e) => setCategory(e.target.value)} />
        </label>
        <label>
          color
          <input required value={color} onChange={(e) => setColor(e.target.value)} />
        </label>
        <label>
          brand
          <input required value={brand} onChange={(e) => setBrand(e.target.value)} />
        </label>
        <label>
          attributes (JSON)
          <textarea rows={8} value={attributes} onChange={(e) => setAttributes(e.target.value)} />
        </label>
        <div className="row">
          <button type="submit" disabled={busy}>
            Save changes
          </button>
          <button type="button" className="danger" disabled={busy} onClick={() => void onDelete()}>
            Delete item
          </button>
        </div>
      </form>
    </div>
  );
}
