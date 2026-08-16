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

API services should call AI through stable functions such as:

```text
generate_outfit_rationale(context)
extract_wardrobe_attributes(image_context)
answer_style_question(user_context, message)
```
