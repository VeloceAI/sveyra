import { AppearanceProfileRequest, SkinDepth, Undertone } from "@/lib/api/types";

export const INITIAL: AppearanceProfileRequest = {
  skin: {
    tone_hex: "#B98267",
    depth: "medium",
    undertone: "neutral",
    sensitive: false,
  },
  face: { shape: "unspecified" },
  eyes: { color: "dark brown" },
  hair: {
    color: "dark brown",
    texture: "wavy",
    chemically_treated: false,
  },
  colour_analysis: { contrast: "medium" },
  makeup: {
    intensity: "natural",
    finish: "natural",
    focus: ["skin"],
    avoid: [],
  },
  evidence: {
    source: "self_reported",
    user_confirmed: true,
    confidence: 1,
  },
};

export const DEPTHS: { value: SkinDepth; label: string; sample: string }[] = [
  { value: "very_light", label: "Very light", sample: "#F0CDB8" },
  { value: "light", label: "Light", sample: "#DDAF91" },
  { value: "medium", label: "Medium", sample: "#B98267" },
  { value: "tan", label: "Tan", sample: "#9A624C" },
  { value: "deep", label: "Deep", sample: "#704536" },
  { value: "very_deep", label: "Very deep", sample: "#442820" },
];

export const UNDERTONES: { value: Undertone; label: string; hint: string }[] = [
  { value: "cool", label: "Cool", hint: "pink, red or blue cast" },
  { value: "neutral", label: "Neutral", hint: "balanced warm and cool" },
  { value: "warm", label: "Warm", hint: "golden, peach or yellow cast" },
  { value: "olive", label: "Olive", hint: "green-gold or muted cast" },
];

export const FOCUS = ["skin", "eyes", "brows", "lips"];

export function title(value: string) {
  return value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

export function Choice<T extends string>({
  value,
  current,
  label,
  onSelect,
}: {
  value: T;
  current: T;
  label: string;
  onSelect: (value: T) => void;
}) {
  return (
    <button
      type="button"
      className="appearance-choice"
      aria-pressed={current === value}
      onClick={() => onSelect(value)}
    >
      {label}
    </button>
  );
}
