"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { createWardrobeItem } from "@/lib/api";
import { formatApiError } from "@/lib/api/client";
import { ErrorBanner } from "@/components/ErrorBanner";

export default function NewWardrobeItemPage() {
  const router = useRouter();
  const [category, setCategory] = useState("shirt");
  const [color, setColor] = useState("navy");
  const [brand, setBrand] = useState("unbranded");
  const [attributes, setAttributes] = useState("{}");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      let attrs: Record<string, unknown> = {};
      if (attributes.trim()) {
        const parsed = JSON.parse(attributes) as unknown;
        if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error("attributes must be a JSON object");
        }
        attrs = parsed as Record<string, unknown>;
      }
      const created = await createWardrobeItem({
        category: category.trim(),
        color: color.trim(),
        brand: brand.trim(),
        attributes: attrs,
      });
      router.push(`/wardrobe/${created.id}`);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="stack">
      <div className="row">
        <h1>New wardrobe item</h1>
        <Link href="/wardrobe">Back</Link>
      </div>
      <ErrorBanner message={error} />
      <form className="card stack" onSubmit={onSubmit}>
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
          attributes (JSON object)
          <textarea rows={4} value={attributes} onChange={(e) => setAttributes(e.target.value)} />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "Creating…" : "Create"}
        </button>
      </form>
    </div>
  );
}
