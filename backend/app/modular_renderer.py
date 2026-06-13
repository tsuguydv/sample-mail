"""Render modular block-based emails via email_builder."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Optional

from app.email_builder import EmailBuilder
from app.email_builder.registry import DESIGN_DEFAULTS
from app.modular_presets import (
    CTA_BLOCK_NAMES,
    IMAGE_BLOCK_NAMES,
    TEXT_BODY_BLOCK_NAMES,
)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def _theme_to_design(
    theme: dict | None,
    company_profile: dict,
    subject: str,
    color_scheme: Optional[str] = None,
) -> dict[str, Any]:
    th = theme or {}
    primary = str(th.get("primary") or "#4f46e5")
    company_name = str(company_profile.get("companyName") or "").strip()
    return {
        **DESIGN_DEFAULTS,
        "brand_name": company_name or subject or DESIGN_DEFAULTS["brand_name"],
        "brand_url": company_profile.get("website") or "#",
        "preheader": subject or DESIGN_DEFAULTS["preheader"],
        "background_color": "#f4f4f5" if (color_scheme or "light") != "dark" else "#111827",
        "surface_color": "#ffffff" if (color_scheme or "light") != "dark" else "#1f2937",
        "primary_color": primary,
        "primary_dark": str(th.get("secondary") or primary),
        "accent_color": str(th.get("accent") or DESIGN_DEFAULTS["accent_color"]),
        "text_color": "#172033" if (color_scheme or "light") != "dark" else "#f9fafb",
        "muted_color": "#5f6f89" if (color_scheme or "light") != "dark" else "#9ca3af",
    }


def inject_generation_content(
    block_layout: list[dict],
    *,
    subject: str,
    body_html: str,
    image_url: Optional[str],
    image_alt: Optional[str],
    cta_link: Optional[str],
    cta_label: Optional[str],
    company_profile: dict,
) -> list[dict]:
    layout = deepcopy(block_layout)
    text_injected = False
    image_injected = False
    cta_injected = False
    company_name = str(company_profile.get("companyName") or "").strip()
    plain_body = _strip_html(body_html)

    def _fill(ctx: dict, key: str, value: Any) -> None:
        if value is None or value == "":
            return
        existing = ctx.get(key)
        if existing is None or existing == "":
            ctx[key] = value
        elif isinstance(existing, list) and not existing:
            ctx[key] = value

    for block in layout:
        if not isinstance(block, dict):
            continue
        name = str(block.get("name") or "").strip()
        ctx = block.setdefault("context", {})
        if not isinstance(ctx, dict):
            ctx = {}
            block["context"] = ctx

        if name == "header":
            _fill(ctx, "logo_text", company_name or "smart-letters")
            niche = str(company_profile.get("niche") or "").strip()
            if niche:
                _fill(ctx, "tagline", niche[:120])
            else:
                _fill(ctx, "tagline", "Генерация email с ИИ")

        if name in {"hero", "hero_split", "hero_compact"}:
            if subject:
                _fill(ctx, "title", subject)
            if plain_body and not text_injected:
                _fill(ctx, "subtitle", plain_body[:280])
            if image_url and name in IMAGE_BLOCK_NAMES and not image_injected:
                ctx.setdefault("image_url", image_url)
                _fill(ctx, "image_alt", image_alt or subject or "Email image")
                image_injected = True
            if cta_link:
                _fill(ctx, "button_url", cta_link)
            if cta_label:
                _fill(ctx, "button_text", cta_label)

        if name == "text" and body_html and not text_injected:
            if not ctx.get("paragraphs"):
                ctx["paragraphs"] = [body_html]
            _fill(ctx, "title", subject)
            text_injected = True

        if name in {"image_full", "image_left", "image_right"} and image_url and not image_injected:
            ctx.setdefault("image_url", image_url)
            _fill(ctx, "image_alt", image_alt or subject or "Email image")
            if plain_body:
                _fill(ctx, "text", plain_body[:400])
            if subject:
                _fill(ctx, "title", subject)
            image_injected = True

        if name in CTA_BLOCK_NAMES and not cta_injected and name not in {"hero", "hero_split", "hero_compact", "promo"}:
            if cta_link:
                _fill(ctx, "button_url", cta_link)
            if cta_label:
                _fill(ctx, "button_text", cta_label)
            cta_injected = True

        if name == "footer":
            _fill(ctx, "company_name", company_name or "smart-letters")
            contact = []
            if company_profile.get("email"):
                contact.append(str(company_profile["email"]))
            if company_profile.get("phone"):
                contact.append(str(company_profile["phone"]))
            if company_profile.get("website"):
                contact.append(str(company_profile["website"]))
            if contact and not ctx.get("address"):
                ctx["address"] = " · ".join(contact)
            elif company_name and not ctx.get("address"):
                ctx["address"] = company_name
            if company_profile.get("website") and not ctx.get("social_links"):
                ctx["social_links"] = [{"title": "Сайт", "url": company_profile["website"]}]

    return layout


def render_modular_email(
    block_layout: list[dict],
    *,
    company_profile: dict,
    subject: str,
    body_html: str = "",
    image_url: Optional[str] = None,
    image_alt: Optional[str] = None,
    cta_link: Optional[str] = None,
    cta_label: Optional[str] = None,
    theme: Optional[dict] = None,
    color_scheme: Optional[str] = None,
    language: str = "ru",
) -> str:
    design = _theme_to_design(theme, company_profile, subject, color_scheme)
    layout = inject_generation_content(
        block_layout,
        subject=subject,
        body_html=body_html,
        image_url=image_url,
        image_alt=image_alt,
        cta_link=cta_link,
        cta_label=cta_label,
        company_profile=company_profile,
    )
    builder = EmailBuilder(design=design)
    for block in layout:
        name = str(block.get("name") or "").strip()
        if not name:
            continue
        ctx = block.get("context")
        builder.add_block(name, ctx if isinstance(ctx, dict) else None)
    return builder.render({"preheader": subject or design.get("preheader", "")})


def layout_needs_image(block_layout: list[dict] | None) -> bool:
    for item in block_layout or []:
        if isinstance(item, dict) and str(item.get("name") or "") in IMAGE_BLOCK_NAMES:
            return True
    return False


def layout_body_count(block_layout: list[dict] | None) -> int:
    count = 0
    for item in block_layout or []:
        if isinstance(item, dict) and str(item.get("name") or "") in TEXT_BODY_BLOCK_NAMES:
            count += 1
    return max(1, count)


def layout_cta_count(block_layout: list[dict] | None) -> int:
    for item in block_layout or []:
        if isinstance(item, dict) and str(item.get("name") or "") in CTA_BLOCK_NAMES:
            return 1
    return 0
