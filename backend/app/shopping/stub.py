from typing import Literal
from app.shopping.port import ShoppingPort, ShoppingProduct


class StubShopping(ShoppingPort):
    """Deterministic mock shopping provider returning realistic test products."""

    def get_recommendations_for_categories(
        self,
        categories: list[Literal["top", "bottom", "shoes"]],
        budget: dict[str, object],
    ) -> list[ShoppingProduct]:
        # Realistic mock product inventory.
        # These are clearly test/demo data, not real live commerce inventory.
        inventory = [
            # Tops
            ShoppingProduct(
                id="stub_top_1",
                name="Minimalist Cotton Crewneck Tee",
                brand="Everlane",
                price=30.0,
                url="https://example.com/demo/everlane-crewneck-tee",
                category="top",
                image_url="https://example.com/demo/images/everlane-crewneck-tee.jpg",
            ),
            ShoppingProduct(
                id="stub_top_2",
                name="Oxford Cotton Button Down",
                brand="Ralph Lauren",
                price=95.0,
                url="https://example.com/demo/polo-oxford-shirt",
                category="top",
                image_url="https://example.com/demo/images/polo-oxford-shirt.jpg",
            ),
            ShoppingProduct(
                id="stub_top_3",
                name="Merino Wool Sweater",
                brand="Uniqlo",
                price=49.9,
                url="https://example.com/demo/uniqlo-merino-sweater",
                category="top",
                image_url="https://example.com/demo/images/uniqlo-merino-sweater.jpg",
            ),
            # Bottoms
            ShoppingProduct(
                id="stub_bottom_1",
                name="511 Slim Fit Jeans",
                brand="Levi's",
                price=69.5,
                url="https://example.com/demo/levis-511",
                category="bottom",
                image_url="https://example.com/demo/images/levis-511.jpg",
            ),
            ShoppingProduct(
                id="stub_bottom_2",
                name="Stretch Washable Chinos",
                brand="Bonobos",
                price=98.0,
                url="https://example.com/demo/bonobos-chinos",
                category="bottom",
                image_url="https://example.com/demo/images/bonobos-chinos.jpg",
            ),
            ShoppingProduct(
                id="stub_bottom_3",
                name="Pleated Linen Trousers",
                brand="Zara",
                price=45.9,
                url="https://example.com/demo/zara-linen-trousers",
                category="bottom",
                image_url="https://example.com/demo/images/zara-linen-trousers.jpg",
            ),
            # Shoes
            ShoppingProduct(
                id="stub_shoes_1",
                name="Classic Leather Sneaker",
                brand="Adidas",
                price=85.0,
                url="https://example.com/demo/adidas-stan-smith",
                category="shoes",
                image_url="https://example.com/demo/images/adidas-stan-smith.jpg",
            ),
            ShoppingProduct(
                id="stub_shoes_2",
                name="ØriginalGrand Wingtip Loafer",
                brand="Cole Haan",
                price=145.0,
                url="https://example.com/demo/cole-haan-loafer",
                category="shoes",
                image_url="https://example.com/demo/images/cole-haan-loafer.jpg",
            ),
            ShoppingProduct(
                id="stub_shoes_3",
                name="Waterproof Chelsea Boot",
                brand="Blundstone",
                price=210.0,
                url="https://example.com/demo/blundstone-boot",
                category="shoes",
                image_url="https://example.com/demo/images/blundstone-boot.jpg",
            ),
        ]

        # Extract budget filters if any
        max_price = budget.get("max")
        preferred_brands = budget.get("brands") or budget.get("preferred_brands")

        filtered = []
        for item in inventory:
            # Must match the requested categories (wardrobe gaps)
            if item.category not in categories:
                continue

            # Respect max price filter if valid number
            if isinstance(max_price, (int, float)):
                if item.price > float(max_price):
                    continue

            # Respect brand preferences if provided
            if isinstance(preferred_brands, list) and preferred_brands:
                normalized_preferred = [
                    str(b).strip().lower() for b in preferred_brands if b
                ]
                if item.brand.lower() not in normalized_preferred:
                    continue

            filtered.append(item)

        return filtered
