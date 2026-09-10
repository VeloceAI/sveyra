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
  media_asset_ids: string[];
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

export type RecommendationConstraints = {
  required_item_ids?: string[];
  excluded_item_ids?: string[];
  replacement_item_id?: string;
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

export type CanonicalAvatarResponse = {
  asset_id: string;
  backend: string;
  stage: "canonical_rigged_seed" | "canonical_parameter_fitted";
  topology_id: string;
  topology_version: string;
  rig_id: string;
  rig_version: string;
  height_cm: number;
  vertex_count: number;
  triangle_count: number;
  joint_count: number;
  rigged: boolean;
  parameter_fitted: boolean;
  identity_fitted: boolean;
  photoreal_ready: boolean;
  deformation_method: string | null;
  supported_measurements: string[];
  applied_measurement_ratios: Record<string, number>;
  clamped_measurements: string[];
  limitations: string[];
};

export type HumanEnginePreviewRequest = {
  height_cm: number;
  shoulder_width_cm?: number;
  shoulder_depth_cm?: number;
  neck_width_cm?: number;
  chest_width_cm?: number;
  chest_depth_cm?: number;
  waist_width_cm?: number;
  waist_depth_cm?: number;
  hip_width_cm?: number;
  hip_depth_cm?: number;
  upper_arm_radius_cm?: number;
  forearm_radius_cm?: number;
  thigh_width_cm?: number;
  thigh_depth_cm?: number;
  calf_width_cm?: number;
  calf_depth_cm?: number;
  ankle_width_cm?: number;
  head_width_cm?: number;
  head_depth_cm?: number;
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

export type SkinDepth = "very_light" | "light" | "medium" | "tan" | "deep" | "very_deep";
export type Undertone = "cool" | "neutral" | "warm" | "olive";
export type ContrastLevel = "low" | "medium" | "high";
export type FaceShape =
  | "unspecified"
  | "oval"
  | "round"
  | "square"
  | "heart"
  | "oblong"
  | "diamond";
export type HairTexture = "straight" | "wavy" | "curly" | "coily" | "protective" | "shaved";
export type MakeupIntensity = "none" | "natural" | "polished" | "statement";
export type MakeupFinish = "natural" | "matte" | "dewy" | "satin";

export type AppearanceProfileRequest = {
  skin: {
    tone_hex: string;
    depth: SkinDepth;
    undertone: Undertone;
    sensitive: boolean;
  };
  face: { shape: FaceShape };
  eyes: { color: string };
  hair: {
    color: string;
    texture: HairTexture;
    chemically_treated: boolean;
  };
  colour_analysis: { contrast: ContrastLevel };
  makeup: {
    intensity: MakeupIntensity;
    finish: MakeupFinish;
    focus: string[];
    avoid: string[];
  };
  evidence: {
    source: "self_reported" | "photo_estimate" | "professional";
    user_confirmed: boolean;
    confidence: number;
  };
};

export type ColourSwatch = { name: string; hex: string };

export type AppearanceProfile = AppearanceProfileRequest & {
  id: string;
  user_id: string;
  palette: {
    title: string;
    summary: string;
    best_colours: ColourSwatch[];
    neutrals: ColourSwatch[];
    metals: string[];
    combinations: {
      name: string;
      colours: ColourSwatch[];
      guidance: string;
    }[];
    makeup: {
      complexion: string;
      cheeks: string;
      lips: string;
      eyes: string;
      finish: string;
    };
  };
  created_at: string | null;
  updated_at: string | null;
};

export type CapabilityStatus = "ready" | "demo" | "setup_required" | "planned";

export type PlatformReadiness = {
  parity_phase: string;
  product_message: string;
  personal_model: {
    style_ready: boolean;
    appearance_ready: boolean;
    body_ready: boolean;
    body_measurement_count: number;
    wardrobe_items: number;
    enriched_items: number;
    core_completion_percent: number;
    next_action: {
      label: string;
      href: string;
      reason: string;
    };
  };
  capabilities: {
    key: string;
    label: string;
    status: CapabilityStatus;
    provider: string;
    summary: string;
    limitation: string | null;
    href: string | null;
  }[];
};
