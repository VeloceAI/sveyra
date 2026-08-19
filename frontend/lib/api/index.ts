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
