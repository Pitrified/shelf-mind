"""Metadata enricher - deterministic metadata extraction from Thing data."""

from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from loguru import logger as lg

from shelf_mind.domain.schemas.metadata_schema import MetadataSchema

# Common category keywords for rule-based enrichment
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "electronics": [
        "phone",
        "laptop",
        "charger",
        "cable",
        "headphone",
        "speaker",
        "tablet",
        "mouse",
        "keyboard",
        "monitor",
        "camera",
        "battery",
        "adapter",
        "usb",
        "remote",
        "controller",
        "console",
        "router",
        "hub",
    ],
    "kitchenware": [
        "pan",
        "pot",
        "spoon",
        "fork",
        "knife",
        "plate",
        "bowl",
        "cup",
        "mug",
        "glass",
        "blender",
        "toaster",
        "kettle",
        "spatula",
        "whisk",
        "grater",
        "peeler",
        "tray",
        "colander",
    ],
    "clothing": [
        "shirt",
        "pants",
        "jacket",
        "coat",
        "shoe",
        "sock",
        "hat",
        "scarf",
        "glove",
        "dress",
        "skirt",
        "sweater",
        "hoodie",
        "belt",
        "tie",
        "boot",
    ],
    "tools": [
        "hammer",
        "screwdriver",
        "wrench",
        "plier",
        "drill",
        "saw",
        "tape",
        "level",
        "clamp",
        "sandpaper",
        "nail",
        "screw",
        "bolt",
    ],
    "furniture": [
        "chair",
        "table",
        "desk",
        "shelf",
        "cabinet",
        "drawer",
        "bed",
        "couch",
        "sofa",
        "lamp",
        "mirror",
        "rug",
        "curtain",
        "stool",
    ],
    "stationery": [
        "pen",
        "pencil",
        "notebook",
        "paper",
        "stapler",
        "eraser",
        "ruler",
        "marker",
        "highlighter",
        "binder",
        "clip",
        "envelope",
        "stamp",
    ],
    "toiletries": [
        "soap",
        "shampoo",
        "toothbrush",
        "toothpaste",
        "towel",
        "razor",
        "comb",
        "brush",
        "lotion",
        "deodorant",
        "tissue",
    ],
    "toys": [
        "toy",
        "game",
        "puzzle",
        "doll",
        "lego",
        "block",
        "ball",
        "figure",
        "board game",
    ],
}

_MATERIAL_KEYWORDS: dict[str, list[str]] = {
    "metal": ["steel", "iron", "aluminum", "copper", "brass", "metal", "tin"],
    "plastic": ["plastic", "polymer", "acrylic", "nylon", "pvc", "silicone"],
    "wood": ["wood", "wooden", "bamboo", "oak", "pine", "walnut", "plywood"],
    "glass": ["glass", "crystal"],
    "ceramic": ["ceramic", "porcelain", "clay"],
    "fabric": ["cotton", "polyester", "linen", "silk", "wool", "leather", "fabric"],
    "paper": ["paper", "cardboard", "cardstock"],
}

_ROOM_KEYWORDS: dict[str, list[str]] = {
    "kitchen": ["kitchen", "cook", "bake", "food", "dish"],
    "bedroom": ["bed", "sleep", "pillow", "mattress", "nightstand"],
    "bathroom": ["bath", "shower", "toilet", "sink"],
    "living room": ["couch", "sofa", "tv", "television", "remote"],
    "garage": ["car", "tool", "drill", "saw", "wrench"],
    "office": ["desk", "computer", "monitor", "keyboard", "pen", "paper"],
    "laundry": ["wash", "iron", "dryer", "detergent"],
}


class MetadataEnricher(ABC):
    """Interface for metadata extraction from Thing data."""

    @abstractmethod
    def enrich(self, name: str, description: str | None = None) -> MetadataSchema:
        """Extract structured metadata from a Thing's name and description.

        Args:
            name: Thing name.
            description: Optional description.

        Returns:
            Populated MetadataSchema.
        """


class RuleBasedMetadataEnricher(MetadataEnricher):
    """Deterministic rule-based metadata enricher.

    Uses keyword matching to assign category, material, room hints,
    and tags. Fully offline and deterministic.
    """

    def enrich(self, name: str, description: str | None = None) -> MetadataSchema:
        """Extract structured metadata using keyword rules.

        Args:
            name: Thing name.
            description: Optional description text.

        Returns:
            Populated MetadataSchema.
        """
        combined = f"{name} {description or ''}".lower()
        tokens = set(combined.split())

        category = self._detect_category(tokens)
        material = self._detect_material(tokens)
        room_hint = self._detect_room(tokens)
        tags = self._extract_tags(name, description)
        usage_context = self._infer_usage(category, room_hint)

        lg.debug(f"Enriched metadata for '{name}': category={category}")

        return MetadataSchema(
            category=category,
            tags=tags,
            material=material,
            room_hint=room_hint,
            usage_context=usage_context,
        )

    @staticmethod
    def _detect_category(tokens: set[str]) -> str:
        """Match tokens against category keyword lists.

        Args:
            tokens: Lowercased words from name+description.

        Returns:
            Best-matching category or "general".
        """
        best_category = "general"
        best_score = 0
        for category, keywords in _CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in tokens)
            if score > best_score:
                best_score = score
                best_category = category
        return best_category

    @staticmethod
    def _detect_material(tokens: set[str]) -> str | None:
        """Match tokens against material keyword lists.

        Args:
            tokens: Lowercased words from name+description.

        Returns:
            Detected material or None.
        """
        for material, keywords in _MATERIAL_KEYWORDS.items():
            if any(kw in tokens for kw in keywords):
                return material
        return None

    @staticmethod
    def _detect_room(tokens: set[str]) -> str | None:
        """Match tokens against room keyword lists.

        Args:
            tokens: Lowercased words from name+description.

        Returns:
            Detected room hint or None.
        """
        best_room = None
        best_score = 0
        for room, keywords in _ROOM_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in tokens)
            if score > best_score:
                best_score = score
                best_room = room
        return best_room

    @staticmethod
    def _extract_tags(name: str, description: str | None) -> list[str]:
        """Build tag list from name and description words.

        Filters out very short words and common stop words.

        Args:
            name: Thing name.
            description: Optional description.

        Returns:
            Cleaned list of tags.
        """
        stop_words = {
            "a",
            "an",
            "the",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "and",
            "or",
            "is",
            "it",
            "my",
            "with",
            "from",
            "this",
            "that",
        }
        combined = f"{name} {description or ''}".lower()
        words = combined.split()
        tags = []
        seen: set[str] = set()
        for word in words:
            cleaned = word.strip(".,;:!?\"'()[]{}").lower()
            if len(cleaned) > 2 and cleaned not in stop_words and cleaned not in seen:  # noqa: PLR2004
                seen.add(cleaned)
                tags.append(cleaned)
        return tags[:30]

    @staticmethod
    def _infer_usage(category: str, room_hint: str | None) -> list[str]:
        """Infer usage contexts from category and room.

        Args:
            category: Detected category.
            room_hint: Detected room.

        Returns:
            List of usage context strings.
        """
        contexts = []
        if category != "general":
            contexts.append(category)
        if room_hint:
            contexts.append(room_hint)
        return contexts
