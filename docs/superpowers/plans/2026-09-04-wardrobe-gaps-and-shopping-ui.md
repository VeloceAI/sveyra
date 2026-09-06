# Wardrobe Gaps and Shopping UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface the wardrobe-gap and shopping endpoints, which are fully built and tested in the backend but have no client function and no screen, so a user can see what their wardrobe is missing and what to buy.

**Architecture:** Two typed client functions over the existing `apiRequest` helper, then one page combining them. Gaps are the input to shopping conceptually, so they belong on one screen rather than two: you look at what is missing and then at what would fill it.

**Tech Stack:** Next.js 15 App Router, React 19, TypeScript, the existing `@/lib/api` client and `ErrorBanner` component.

**Spec:** Derived from the live backend contracts in `backend/app/schemas/gap_schema.py` and `backend/app/schemas/shopping_schema.py`.

## Global Constraints

- Both endpoints are `POST` and take an **empty JSON body** (`{}`). `GapRequest` and `ShoppingRequest` are empty strict models; sending any field returns 422.
- Both require a Bearer token. `apiRequest` attaches it by default.
- `WardrobeGap.category` is exactly `"top" | "bottom" | "shoes"`. `priority` is exactly `"high"`.
- `ShoppingProduct` fields: `id`, `name`, `brand`, `price` (number), `url`, `category`, `image_url` (nullable).
- Shopping returns **mock products with `example.com` URLs**. The UI must say so rather than implying a real storefront.
- No new dependency. Styles go in `frontend/app/globals.css`, matching existing class naming.

---

### Task 1: Types and client functions

**Files:**
- Modify: `frontend/lib/api/types.ts`
- Modify: `frontend/lib/api/index.ts`

**Interfaces:**
- Produces: `WardrobeGap`, `GapResponse`, `ShoppingProduct`, `ShoppingResponse` types; `getWardrobeGaps(): Promise<GapResponse>` and `getShoppingRecommendations(): Promise<ShoppingResponse>`.

- [ ] **Step 1: Add the types**

```ts
export type GapCategory = "top" | "bottom" | "shoes";

export type WardrobeGap = {
  category: GapCategory;
  priority: "high";
  reason: string;
};

export type GapResponse = { gaps: WardrobeGap[] };

export type ShoppingProduct = {
  id: string;
  name: string;
  brand: string;
  price: number;
  url: string;
  category: GapCategory;
  image_url: string | null;
};

export type ShoppingResponse = { products: ShoppingProduct[] };
```

- [ ] **Step 2: Add the client functions**

Both endpoints take an empty body. Passing `{}` is required: omitting `body`
would make `apiRequest` send a GET.

```ts
export function getWardrobeGaps() {
  return apiRequest<GapResponse>("/v1/recommendations/gaps", {
    method: "POST",
    body: {},
  });
}

export function getShoppingRecommendations() {
  return apiRequest<ShoppingResponse>("/v1/recommendations/shopping", {
    method: "POST",
    body: {},
  });
}
```

- [ ] **Step 3: Verify it typechecks**

Run: `npm --workspace @sveyra/web run typecheck`
Expected: exit 0

---

### Task 2: The gaps and shopping page

**Files:**
- Create: `frontend/app/(app)/gaps/page.tsx`
- Modify: `frontend/components/AppNav.tsx`
- Modify: `frontend/app/globals.css`

**Interfaces:**
- Consumes: `getWardrobeGaps`, `getShoppingRecommendations`, and the types from Task 1.

- [ ] **Step 1: Write the page**

Load both on mount. Gaps come first because shopping only makes sense once you
know what is missing. An empty gap list is a success state, not an error: it
means the wardrobe covers the basics.

Key behaviours:
- A wardrobe with no gaps shows a positive empty state, not a blank screen.
- Products are grouped under the gap they fill.
- The mock catalogue is labelled as such.

- [ ] **Step 2: Add the nav link**

```tsx
{ href: "/gaps", label: "Gaps" },
```

- [ ] **Step 3: Add styles to globals.css**

Reuse the existing muted/error/numeric conventions.

- [ ] **Step 4: Verify**

Run: `npm --workspace @sveyra/web run typecheck && npm --workspace @sveyra/web run lint && npm --workspace @sveyra/web run build`
Expected: all exit 0, route `/gaps` listed in the build output.

- [ ] **Step 5: Verify against a running server**

Register a user, add no wardrobe items, and confirm the page reports three
high-priority gaps. Add a top, a bottom and shoes, and confirm the gaps clear.

- [ ] **Step 6: Commit**

---

## Self-Review

**Spec coverage:** Both endpoints (`/gaps`, `/shopping`) get a client function and a screen. Both are reachable from the nav.

**Placeholders:** None. Every code step contains the actual code.

**Type consistency:** `GapCategory` is used by both `WardrobeGap` and `ShoppingProduct`, matching the backend `Literal["top", "bottom", "shoes"]` in both schemas. Function names used in Task 2 match those defined in Task 1.
