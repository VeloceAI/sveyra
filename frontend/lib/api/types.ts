export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
  };
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export type RegisterResponse = {
  id: string;
  email: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type PersistedProfile = {
  user_id: string;
  email: string;
  style_profile_id: string;
  preferences: Record<string, unknown>;
  dislikes: Record<string, unknown>;
  budget: Record<string, unknown>;
  created_at: string | null;
};

export type ProfilePersistRequest = {
  preferences: Record<string, unknown>;
  dislikes: Record<string, unknown>;
  budget: Record<string, unknown>;
};

export type BodyProfile = {
  id: string;
  user_id: string;
  measurements: Record<string, unknown>;
  fit_preferences: Record<string, unknown>;
};

export type BodyProfileListResponse = {
  body_profiles: BodyProfile[];
  limit: number;
  offset: number;
  total: number;
};

export type WardrobeItem = {
  id: string;
  user_id: string;
  category: string;
  color: string;
  brand: string;
  attributes: Record<string, unknown>;
};

export type WardrobeItemListResponse = {
  wardrobe_items: WardrobeItem[];
  limit: number;
  offset: number;
  total: number;
};

export type WardrobeItemCreateRequest = {
  category: string;
  color: string;
  brand: string;
  attributes: Record<string, unknown>;
};

export type WardrobeItemUpdateRequest = {
  category?: string;
  color?: string;
  brand?: string;
  attributes?: Record<string, unknown>;
};

export type MediaAsset = {
  id: string;
  user_id: string;
  wardrobe_item_id: string | null;
  reference: string;
};

export type MediaAssetAccessResponse = {
  url: string;
};

export type RecommendationCandidate = {
  item_ids: string[];
  rationale: string;
};

export type RecommendationResponse = {
  occasion: string;
  recommendations: RecommendationCandidate[];
};

export type Outfit = {
  id: string;
  user_id: string;
  occasion: string;
  item_ids: string[];
  rationale: Record<string, unknown>;
};

export type OutfitListResponse = {
  outfits: Outfit[];
  limit: number;
  offset: number;
  total: number;
};

export type OutfitCreateRequest = {
  occasion: string;
  item_ids: string[];
  rationale: Record<string, unknown>;
};

export type AvatarBuildResponse = {
  asset_id: string;
  backend: string;
  source_views: number;
  measurements: Record<string, number>;
  body_parameters: Record<string, number | null>;
  confidence: { overall: number; views: Record<string, number>; warnings: string[] };
  profiling_ms: Record<string, number>;
};

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

export type WearLog = {
  id: string;
  user_id: string;
  worn_on: string;
  outfit_id: string | null;
  item_ids: string[];
  occasion: string | null;
  note: string | null;
  planned: boolean;
};

export type WearLogListResponse = {
  entries: WearLog[];
  start: string;
  end: string;
  total: number;
};

export type WardrobeUsageResponse = {
  most_worn: { item_id: string; times_worn: number }[];
  never_worn_item_ids: string[];
  logged_days: number;
};

export type CaptureInstruction = {
  severity: "blocking" | "advisory";
  message: string;
  code: string;
};

export type CaptureViewGuidance = {
  view: string;
  usable: boolean;
  framing_score: number;
  instructions: CaptureInstruction[];
};

export type CaptureCheckResponse = {
  ready: boolean;
  views: Record<string, CaptureViewGuidance>;
  overall: string[];
};
