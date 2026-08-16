class ProfileRepository:
    def get_demo_profile(self) -> dict[str, object]:
        return {
            "user_id": "demo",
            "style_words": ["minimal", "sharp", "comfortable"],
            "wardrobe_items": 0,
            "fit_profile_ready": False,
            "avatar_ready": False,
        }
