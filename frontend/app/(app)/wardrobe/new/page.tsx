"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import {
  createWardrobeItem,
  enrichWardrobeItem,
  uploadMedia,
} from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import type { WardrobeItem } from "@/lib/api/types";
import { rememberMediaAsset } from "@/lib/auth/session";

type SelectedPhoto = { id: string; file: File; url: string };
type ImportStage = "queued" | "creating" | "uploading" | "identifying" | "done" | "error";
type ImportResult = {
  id: string;
  name: string;
  stage: ImportStage;
  item?: WardrobeItem;
  message?: string;
};

const STAGE_LABEL: Record<ImportStage, string> = {
  queued: "Queued",
  creating: "Creating item",
  uploading: "Saving photo",
  identifying: "Identifying",
  done: "Ready to review",
  error: "Needs attention",
};

export default function NewWardrobeItemPage() {
  const [photos, setPhotos] = useState<SelectedPhoto[]>([]);
  const [brand, setBrand] = useState("");
  const [category, setCategory] = useState("");
  const [color, setColor] = useState("");
  const [autoIdentify, setAutoIdentify] = useState(true);
  const [results, setResults] = useState<ImportResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => () => {
    photos.forEach((photo) => URL.revokeObjectURL(photo.url));
  }, [photos]);

  function selectPhotos(files: FileList | null) {
    setPhotos((current) => {
      current.forEach((photo) => URL.revokeObjectURL(photo.url));
      return Array.from(files ?? []).map((file, index) => ({
        id: `${file.name}-${file.size}-${file.lastModified}-${index}`,
        file,
        url: URL.createObjectURL(file),
      }));
    });
    setResults([]);
    setError(null);
  }

  function updateResult(id: string, change: Partial<ImportResult>) {
    setResults((current) => current.map((result) => (
      result.id === id ? { ...result, ...change } : result
    )));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (photos.length === 0) {
      setError("Choose at least one garment photo.");
      return;
    }

    setBusy(true);
    setError(null);
    setResults(photos.map((photo) => ({
      id: photo.id,
      name: photo.file.name,
      stage: "queued",
    })));

    let failures = 0;
    for (const photo of photos) {
      let created: WardrobeItem | undefined;
      try {
        updateResult(photo.id, { stage: "creating" });
        created = await createWardrobeItem({
          category: category.trim() || "garment",
          color: color.trim() || "unknown",
          brand: brand.trim() || "unbranded",
          attributes: {
            ingestion: {
              source: "photo",
              status: "uploaded",
              user_confirmed: false,
            },
          },
        });

        updateResult(photo.id, { stage: "uploading", item: created });
        const asset = await uploadMedia(photo.file, created.id);
        rememberMediaAsset(created.id, asset.id);

        let item = { ...created, media_asset_ids: [asset.id] };
        if (autoIdentify) {
          updateResult(photo.id, { stage: "identifying", item });
          item = await enrichWardrobeItem(created.id);
        }
        updateResult(photo.id, { stage: "done", item });
      } catch (caught) {
        failures += 1;
        updateResult(photo.id, {
          stage: "error",
          item: created,
          message: formatApiError(caught),
        });
      }
    }

    if (failures > 0) {
      setError(`${failures} item${failures === 1 ? "" : "s"} could not finish processing.`);
    }
    setBusy(false);
  }

  const completed = results.filter((result) => result.stage === "done").length;

  return (
    <section className="closet-import">
      <header className="closet-import-hero">
        <div>
          <p className="closet-kicker">PHOTO-FIRST CLOSET</p>
          <h1>Add clothes,<br />not admin.</h1>
          <p>
            Choose one photo or a batch. SVEYRA creates each item, stores its image,
            and sends it through the configured garment-vision adapter.
          </p>
        </div>
        <Link href="/wardrobe">Back to closet</Link>
      </header>

      <ErrorBanner message={error} />

      <form className="closet-import-form" onSubmit={onSubmit}>
        <label className="closet-dropzone">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            disabled={busy}
            onChange={(event) => selectPhotos(event.target.files)}
          />
          <span>Drop garment photos here</span>
          <small>or choose JPEG, PNG, or WebP · up to 25 MB each</small>
        </label>

        {photos.length > 0 ? (
          <div className="closet-photo-grid">
            {photos.map((photo) => (
              <figure key={photo.id}>
                {/* Local previews never leave this browser. */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photo.url} alt="" />
                <figcaption>{photo.file.name}</figcaption>
              </figure>
            ))}
          </div>
        ) : null}

        <section className="closet-import-options">
          <div>
            <h2>Optional hints</h2>
            <p>Leave these blank and review the detected details afterward.</p>
          </div>
          <div className="closet-hint-grid">
            <label>Brand<input value={brand} onChange={(event) => setBrand(event.target.value)} placeholder="Unbranded" /></label>
            <label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="Detect from photo" /></label>
            <label>Color<input value={color} onChange={(event) => setColor(event.target.value)} placeholder="Detect from photo" /></label>
          </div>
          <label className="closet-toggle">
            <input
              type="checkbox"
              checked={autoIdentify}
              onChange={(event) => setAutoIdentify(event.target.checked)}
            />
            <span>
              <strong>Identify after upload</strong>
              <small>Results are suggestions until you confirm them.</small>
            </span>
          </label>
        </section>

        <button className="closet-import-button" type="submit" disabled={busy || photos.length === 0}>
          {busy
            ? "Building your closet…"
            : photos.length === 0
              ? "Choose garment photos"
              : `Add ${photos.length} item${photos.length === 1 ? "" : "s"}`}
        </button>
      </form>

      {results.length > 0 ? (
        <section className="closet-import-results">
          <header>
            <div><p>IMPORT QUEUE</p><h2>{completed} of {results.length} ready</h2></div>
            {completed > 0 ? <Link href="/wardrobe">View closet →</Link> : null}
          </header>
          <ul>
            {results.map((result) => (
              <li key={result.id}>
                <span className={`import-state is-${result.stage}`} />
                <div>
                  <strong>{result.name}</strong>
                  <small>{STAGE_LABEL[result.stage]}</small>
                  {result.item && result.stage === "done" ? (
                    <p>{result.item.color} · {result.item.category} · {result.item.brand}</p>
                  ) : null}
                  {result.message ? <p className="import-error">{result.message}</p> : null}
                </div>
                {result.item ? <Link href={`/wardrobe/${result.item.id}`}>Review</Link> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}
