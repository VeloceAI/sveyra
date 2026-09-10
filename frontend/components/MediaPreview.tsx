"use client";

import { useEffect, useState } from "react";
import { fetchMediaObjectUrl, getMediaAccess } from "@/lib/api";
import { formatApiError, isBrowserLoadableUrl } from "@/lib/api/client";

export function MediaPreview({
  assetId,
  alt = "Garment",
}: {
  assetId: string | null;
  alt?: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!assetId) {
      setUrl(null);
      setError(null);
      return;
    }
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);

    getMediaAccess(assetId)
      .then(async (response) => {
        const resolved = isBrowserLoadableUrl(response.url)
          ? response.url
          : await fetchMediaObjectUrl(assetId);
        if (cancelled) {
          if (resolved.startsWith("blob:")) URL.revokeObjectURL(resolved);
          return;
        }
        if (resolved.startsWith("blob:")) objectUrl = resolved;
        setUrl(resolved);
      })
      .catch((caught) => {
        if (!cancelled) setError(formatApiError(caught));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [assetId]);

  if (!assetId) {
    return <div className="media-frame"><span className="empty">No photo yet.</span></div>;
  }
  if (loading) {
    return <div className="media-frame"><span className="empty">Loading image…</span></div>;
  }
  if (error) {
    return (
      <div className="media-frame" title={error}>
        <span className="empty">Preview unavailable.</span>
      </div>
    );
  }
  if (!url) {
    return <div className="media-frame"><span className="empty">No preview available.</span></div>;
  }

  return (
    <div className="media-frame">
      {/* Signed HTTPS and authenticated object URLs both expire outside this view. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt={alt} />
    </div>
  );
}
