"use client";

import { useEffect, useState } from "react";
import { getMediaAccess } from "@/lib/api";
import { formatApiError, isBrowserLoadableUrl } from "@/lib/api/client";
import { ErrorBanner } from "@/components/ErrorBanner";

export function MediaPreview({ assetId }: { assetId: string | null }) {
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
    setLoading(true);
    setError(null);
    getMediaAccess(assetId)
      .then((res) => {
        if (!cancelled) setUrl(res.url);
      })
      .catch((err) => {
        if (!cancelled) setError(formatApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [assetId]);

  if (!assetId) {
    return (
      <div className="media-frame">
        <span className="empty">No linked media asset in this browser session.</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="media-frame">
        <span className="empty">Loading access URL…</span>
      </div>
    );
  }

  if (error) return <ErrorBanner message={error} />;

  if (url && !isBrowserLoadableUrl(url)) {
    return (
      <div className="notice">
        Image preview unavailable: the API returned a non-browser URL
        (<span className="mono">{url.startsWith("memory://") ? "memory://…" : "non-http(s)"}</span>
        ). This is expected with <code>STORAGE_BACKEND=memory</code>. Configure GCS for HTTPS signed
        URLs.
      </div>
    );
  }

  if (!url) {
    return (
      <div className="media-frame">
        <span className="empty">No preview URL.</span>
      </div>
    );
  }

  return (
    <div className="media-frame">
      {/* Access URLs are ephemeral signed HTTPS (or local placeholders). */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={url} alt="Garment" />
    </div>
  );
}
