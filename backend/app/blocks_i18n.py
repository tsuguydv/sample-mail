"""Localized block metadata for the template builder UI."""
from __future__ import annotations

from app.email_builder.registry import BLOCK_REGISTRY

BLOCK_DESCRIPTIONS_EN: dict[str, str] = {
    "header": "Email header with logo, tagline, and web view link.",
    "hero": "Main hero with headline, subheadline, CTA, and optional image.",
    "hero_split": "Two-column hero: copy on one side, image on the other.",
    "hero_compact": "Compact hero banner without an image.",
    "text": "Text block with heading and paragraphs.",
    "text_quote": "Quote or highlighted testimonial.",
    "image_left": "Two columns: image left, text right.",
    "image_right": "Two columns: text left, image right.",
    "image_full": "Full-width image block.",
    "gallery": "Image gallery grid.",
    "video_preview": "Video preview block with thumbnail.",
    "cta": "Call-to-action button.",
    "cta_banner": "Full-width CTA banner.",
    "benefits": "Benefits or feature highlights.",
    "feature_list": "Bulleted feature list.",
    "icon_text": "Icons with short descriptions.",
    "statistics": "Key metrics or statistics.",
    "social_proof": "Social proof / trust block.",
    "testimonials": "Customer testimonials.",
    "case_study": "Case study highlight.",
    "client_logos": "Client logo row.",
    "team": "Team member grid.",
    "employee": "Single team member spotlight.",
    "product_card": "Single product card.",
    "product_grid": "Product grid.",
    "pricing_table": "Pricing plan comparison.",
    "service_card": "Service offering card.",
    "faq": "FAQ accordion-style list.",
    "timeline": "Step-by-step timeline.",
    "promo": "Promotional offer block.",
    "coupon": "Coupon / promo code block.",
    "divider": "Visual divider between sections.",
    "spacer": "Vertical spacer.",
    "footer": "Footer with company info and unsubscribe link.",
    "article_list": "List of articles or news items.",
}

FIELD_LABELS_RU: dict[str, str] = {
    "logo_text": "Текст логотипа",
    "tagline": "Подпись",
    "view_url": "Ссылка «Открыть в браузере»",
    "view_text": "Текст ссылки",
    "eyebrow": "Надзаголовок",
    "title": "Заголовок",
    "subtitle": "Подзаголовок",
    "button_text": "Текст кнопки",
    "button_url": "Ссылка кнопки",
    "image_url": "URL изображения",
    "image_alt": "Alt-текст изображения",
    "paragraphs": "Абзацы (разделяйте пустой строкой)",
    "quote": "Цитата",
    "author": "Автор",
    "role": "Должность",
    "text": "Текст",
    "company_name": "Название компании",
    "address": "Контактная строка",
    "unsubscribe_url": "Ссылка отписки",
    "unsubscribe_text": "Текст отписки",
    "height": "Высота отступа (px)",
    "code": "Промокод",
    "discount": "Скидка",
    "label": "Метка",
}

FIELD_LABELS_EN: dict[str, str] = {
    "logo_text": "Logo text",
    "tagline": "Tagline",
    "view_url": "Web view URL",
    "view_text": "Web view link text",
    "eyebrow": "Eyebrow",
    "title": "Title",
    "subtitle": "Subtitle",
    "button_text": "Button text",
    "button_url": "Button URL",
    "image_url": "Image URL",
    "image_alt": "Image alt text",
    "paragraphs": "Paragraphs (separate with a blank line)",
    "quote": "Quote",
    "author": "Author",
    "role": "Role",
    "text": "Text",
    "company_name": "Company name",
    "address": "Contact line",
    "unsubscribe_url": "Unsubscribe URL",
    "unsubscribe_text": "Unsubscribe text",
    "height": "Spacer height (px)",
    "code": "Promo code",
    "discount": "Discount",
    "label": "Label",
}


def localized_blocks(lang: str | None) -> list[dict]:
    lang = (lang or "ru").lower()
    use_en = lang.startswith("en")
    field_labels = FIELD_LABELS_EN if use_en else FIELD_LABELS_RU
    out = []
    for meta in BLOCK_REGISTRY.values():
        desc = BLOCK_DESCRIPTIONS_EN.get(meta.name, meta.description) if use_en else meta.description
        params = {}
        for key, _hint in meta.parameters.items():
            params[key] = field_labels.get(key, _hint)
        out.append(
            {
                "name": meta.name,
                "description": desc,
                "parameters": params,
                "example": meta.example,
            }
        )
    return out
