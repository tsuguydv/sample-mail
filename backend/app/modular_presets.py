"""Modular email template presets (block layouts from sample-mail)."""

MODULAR_TEMPLATE_DEFS: dict[str, dict] = {
    "m1": {
        "name": "template.m1",
        "previewImageUrl": "https://placehold.co/600x400/4f46e5/ffffff?text=Welcome",
        "isModular": True,
        "objectCounts": {"header": 1, "body": 1, "image": 1, "cta": 1, "footer": 1},
        "theme": {
            "primary": "#4f46e5",
            "secondary": "#4338ca",
            "accent": "#e0e7ff",
            "surface": "#ffffff",
            "colorScheme": "light",
        },
        "blockLayout": [
            {"name": "header"},
            {"name": "hero"},
            {"name": "text"},
            {"name": "cta"},
            {"name": "footer"},
        ],
    },
    "m2": {
        "name": "template.m2",
        "previewImageUrl": "https://placehold.co/600x400/4338ca/ffffff?text=B2B",
        "isModular": True,
        "objectCounts": {"header": 1, "body": 1, "image": 1, "cta": 1, "footer": 1},
        "theme": {
            "primary": "#4f46e5",
            "secondary": "#4338ca",
            "accent": "#ddd6fe",
            "surface": "#ffffff",
            "colorScheme": "light",
        },
        "blockLayout": [
            {"name": "header"},
            {"name": "hero_split"},
            {"name": "benefits"},
            {"name": "cta"},
            {"name": "footer"},
        ],
    },
    "m3": {
        "name": "template.m3",
        "previewImageUrl": "https://placehold.co/600x400/7c3aed/ffffff?text=Promo",
        "isModular": True,
        "objectCounts": {"header": 1, "body": 1, "image": 0, "cta": 1, "footer": 1},
        "theme": {
            "primary": "#4f46e5",
            "secondary": "#4338ca",
            "accent": "#ede9fe",
            "surface": "#ffffff",
            "colorScheme": "light",
        },
        "blockLayout": [
            {"name": "header"},
            {"name": "hero_compact"},
            {"name": "promo"},
            {"name": "cta_banner"},
            {"name": "footer"},
        ],
    },
    "m4": {
        "name": "template.m4",
        "previewImageUrl": "https://placehold.co/600x400/4f46e5/ffffff?text=Corporate",
        "isModular": True,
        "objectCounts": {"header": 1, "body": 1, "image": 0, "cta": 0, "footer": 1},
        "theme": {
            "primary": "#4f46e5",
            "secondary": "#6b7280",
            "accent": "#e5e7eb",
            "surface": "#ffffff",
            "colorScheme": "light",
        },
        "blockLayout": [
            {"name": "header"},
            {"name": "text"},
            {"name": "feature_list"},
            {"name": "footer"},
        ],
    },
    "m5": {
        "name": "template.m5",
        "previewImageUrl": "https://placehold.co/600x400/4338ca/ffffff?text=Shop",
        "isModular": True,
        "objectCounts": {"header": 1, "body": 1, "image": 1, "cta": 1, "footer": 1},
        "theme": {
            "primary": "#4f46e5",
            "secondary": "#4338ca",
            "accent": "#fee2e2",
            "surface": "#ffffff",
            "colorScheme": "light",
        },
        "blockLayout": [
            {"name": "header"},
            {"name": "promo"},
            {"name": "product_grid"},
            {"name": "cta"},
            {"name": "footer"},
        ],
    },
    "custom": {
        "name": "template.custom",
        "previewImageUrl": "https://placehold.co/600x400/6366f1/ffffff?text=Custom",
        "isModular": True,
        "objectCounts": {"header": 1, "body": 1, "image": 1, "cta": 1, "footer": 1},
        "theme": {
            "primary": "#6366f1",
            "secondary": "#4338ca",
            "accent": "#e0e7ff",
            "surface": "#ffffff",
            "colorScheme": "light",
        },
        "blockLayout": [
            {"name": "header"},
            {"name": "hero"},
            {"name": "text"},
            {"name": "cta"},
            {"name": "footer"},
        ],
    },
}

IMAGE_BLOCK_NAMES = frozenset(
    {
        "hero",
        "hero_split",
        "hero_compact",
        "image_left",
        "image_right",
        "image_full",
        "gallery",
        "video_preview",
        "product_card",
        "product_grid",
    }
)

TEXT_BODY_BLOCK_NAMES = frozenset(
    {
        "text",
        "text_quote",
        "hero",
        "hero_split",
        "hero_compact",
        "benefits",
        "feature_list",
        "promo",
        "article_list",
        "case_study",
        "service_card",
        "faq",
    }
)

CTA_BLOCK_NAMES = frozenset(
    {
        "cta",
        "cta_banner",
        "hero",
        "hero_split",
        "hero_compact",
        "promo",
        "coupon",
        "service_card",
        "product_card",
    }
)


def object_counts_from_layout(block_layout: list[dict] | None) -> dict:
    layout = block_layout or []
    image = 0
    body = 0
    cta = 0
    for item in layout:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if name in IMAGE_BLOCK_NAMES:
            image = 1
        if name in TEXT_BODY_BLOCK_NAMES:
            body += 1
        if name in CTA_BLOCK_NAMES:
            cta = 1
    return {
        "header": 1,
        "body": max(1, body),
        "image": image,
        "cta": cta,
        "footer": 1,
    }
