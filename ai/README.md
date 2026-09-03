# AI Package

Owns AI orchestration contracts for SVEYRA.

## Responsibilities

- Conversational stylist flows
- Outfit explanation generation
- Wardrobe understanding prompts
- Shopping recommendation reasoning
- Prompt versioning
- Model provider abstraction

## Contract

API services should call AI through stable ports/functions such as:

```text
StylistPort.recommend(RankingContext) -> ranked outfits
VisionPort.analyze_garment(image bytes) -> GarmentAnalysis
generate_outfit_rationale(context)   # future conversational flows
answer_style_question(user_context, message)
```

The backend default stylist is deterministic (`STYLIST_BACKEND=stub`). Real LLM providers remain future adapters behind `StylistPort`.