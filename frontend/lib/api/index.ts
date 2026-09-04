import { apiRequest, apiUpload } from "@/lib/api/client";
import type {
  BodyProfile,
  BodyProfileListResponse,
  MediaAsset,
  MediaAssetAccessResponse,
  Outfit,
  OutfitCreateRequest,
  OutfitListResponse,
  PersistedProfile,
  ProfilePersistRequest,
  RecommendationResponse,
  AvatarBuildResponse,
  GapResponse,
  WardrobeUsageResponse,
  WearLog,
  WearLogListResponse,
  ShoppingResponse,
  RegisterResponse,
  TokenResponse,
  WardrobeItem,
  WardrobeItemCreateRequest,
  WardrobeItemListResponse,
  WardrobeItemUpdateRequest,
} from "@/lib/api/types";

export function register(email: string, password: string) {
  return apiRequest<RegisterResponse>("/v1/auth/register", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export function login(email: string, password: string) {
  return apiRequest<TokenResponse>("/v1/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export async function logout(refreshToken: string) {
  // Revoking server-side matters more than the response: a token left valid
  // outlives the browser session that discarded it.
  await apiRequest<void>("/v1/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
    auth: false,
  });
}

export function buildAvatar(
  heightCm: number,
  photos: { front: File; side?: File | null; back?: File | null },
) {
  const form = new FormData();
  form.append("height_cm", String(heightCm));
  form.append("front", photos.front);
  if (photos.side) form.append("side", photos.side);
  if (photos.back) form.append("back", photos.back);
  return apiUpload<AvatarBuildResponse>("/v1/avatar/build", form);
}

export async function fetchMediaObjectUrl(assetId: string): Promise<string> {
  // The viewer needs bytes, and an in-memory storage backend has no URL a
  // browser can follow. Fetching with the session token works for every backend.
  const { getAccessToken } = await import("@/lib/auth/session");
  const response = await fetch(`/v1/media/${assetId}/content`, {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("Could not download the avatar.");
  return URL.createObjectURL(await response.blob());
}

export function listCalendar(start?: string, end?: string) {
  const query = new URLSearchParams();
  if (start) query.set("start", start);
  if (end) query.set("end", end);
  const suffix = query.toString() ? `?${query}` : "";
  return apiRequest<WearLogListResponse>(`/v1/calendar${suffix}`);
}

export function logWear(entry: {
  worn_on: string;
  item_ids?: string[];
  occasion?: string | null;
  note?: string | null;
  planned?: boolean;
}) {
  return apiRequest<WearLog>("/v1/calendar", { method: "POST", body: entry });
}

export function deleteWearLog(wornOn: string) {
  return apiRequest<void>(`/v1/calendar/${wornOn}`, { method: "DELETE" });
}

export function getWardrobeUsage() {
  return apiRequest<WardrobeUsageResponse>("/v1/calendar/usage");
}

export function getWardrobeGaps() {
  // Both endpoints take an empty body. Passing {} is required: without a body
  // apiRequest would send a GET.
  return apiRequest<GapResponse>("/v1/recommendations/gaps", { method: "POST", body: {} });
}

export function getShoppingRecommendations() {
  return apiRequest<ShoppingResponse>("/v1/recommendations/shopping", {
    method: "POST",
    body: {},
  });
}

export function getCurrentProfile() {
  return apiRequest<PersistedProfile>("/v1/profile");
}

export function saveProfile(payload: ProfilePersistRequest) {
  return apiRequest<PersistedProfile>("/v1/profile", {
    method: "POST",
    body: payload,
  });
}

export function listBodyProfiles(userId: string) {
  return apiRequest<BodyProfileListResponse>(`/v1/profile/${userId}/body`);
}

export function createBodyProfile(
  userId: string,
  payload: { measurements: Record<string, unknown>; fit_preferences: Record<string, unknown> },
) {
  return apiRequest<BodyProfile>(`/v1/profile/${userId}/body`, {
    method: "POST",
    body: payload,
  });
}

export function listWardrobe() {
  return apiRequest<WardrobeItemListResponse>("/v1/wardrobe");
}

export function getWardrobeItem(itemId: string) {
  return apiRequest<WardrobeItem>(`/v1/wardrobe/${itemId}`);
}

export function createWardrobeItem(payload: WardrobeItemCreateRequest) {
  return apiRequest<WardrobeItem>("/v1/wardrobe", {
    method: "POST",
    body: payload,
  });
}

export function patchWardrobeItem(itemId: string, payload: WardrobeItemUpdateRequest) {
  return apiRequest<WardrobeItem>(`/v1/wardrobe/${itemId}`, {
    method: "PATCH",
    body: payload,
  });
}

export function deleteWardrobeItem(itemId: string) {
  return apiRequest<void>(`/v1/wardrobe/${itemId}`, { method: "DELETE" });
}

export function enrichWardrobeItem(itemId: string) {
  return apiRequest<WardrobeItem>(`/v1/wardrobe/${itemId}/enrich`, { method: "POST" });
}

export function uploadMedia(file: File, wardrobeItemId?: string) {
  const form = new FormData();
  form.append("file", file);
  if (wardrobeItemId) form.append("wardrobe_item_id", wardrobeItemId);
  return apiUpload<MediaAsset>("/v1/media/upload", form);
}

export function getMediaAccess(assetId: string) {
  return apiRequest<MediaAssetAccessResponse>(`/v1/media/${assetId}/access`);
}

export function getRecommendations(occasion: string) {
  return apiRequest<RecommendationResponse>("/v1/recommendations", {
    method: "POST",
    body: { occasion },
  });
}

export function listOutfits() {
  return apiRequest<OutfitListResponse>("/v1/outfits");
}

export function getOutfit(outfitId: string) {
  return apiRequest<Outfit>(`/v1/outfits/${outfitId}`);
}

export function createOutfit(payload: OutfitCreateRequest) {
  return apiRequest<Outfit>("/v1/outfits", {
    method: "POST",
    body: payload,
  });
}
