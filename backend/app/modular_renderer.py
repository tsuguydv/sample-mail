"""Render modular block-based emails via email_builder."""
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Optional

from app.email_builder import EmailBuilder
from app.email_builder.registry import DESIGN_DEFAULTS, get_block_example
from app.modular_presets import (
    CTA_BLOCK_NAMES,
    IMAGE_BLOCK_NAMES,
    TEXT_BODY_BLOCK_NAMES,
)

_PLACEHOLDER_RE = re.compile(r"via\.placeholder\.com|placehold\.co")


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def _block_fields(name: str) -> set[str]:
    try:
        return set(get_block_example(name).keys())
    except Exception:
        return set()


def _apply_generated_images(value, image_url: str, image_alt: str) -> None:
    """Recursively fill empty/placeholder image fields with the generated picture.

    Runs on the *merged* block context (registry example + injected content), so it also
    replaces the example placeholder images of composite blocks (gallery/product_grid/…).
    Only invoked when a real ``image_url`` is available, so previews keep their examples.
    """
    if isinstance(value, dict):
        for k, v in list(value.items()):
            kl = str(k).lower()
            if isinstance(v, str):
                if kl == "image_url":
                    if v == "" or _PLACEHOLDER_RE.search(v):
                        value[k] = image_url
                elif kl == "image_alt":
                    if v == "":
                        value[k] = image_alt
                elif _PLACEHOLDER_RE.search(v):
                    value[k] = image_url
            else:
                _apply_generated_images(v, image_url, image_alt)
    elif isinstance(value, list):
        for item in value:
            _apply_generated_images(item, image_url, image_alt)


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
    block_content: Optional[dict] = None,
) -> list[dict]:
    layout = deepcopy(block_layout)
    company_name = str(company_profile.get("companyName") or "").strip()
    plain_body = _strip_html(body_html)
    # JSON-serialized block_content may carry string keys; normalize to int indices.
    bc: dict[int, dict] = {}
    for k, v in (block_content or {}).items():
        try:
            bc[int(k)] = v if isinstance(v, dict) else {}
        except (TypeError, ValueError):
            continue

    def _fill(ctx: dict, key: str, value: Any) -> None:
        if value is None or value == "":
            return
        existing = ctx.get(key)
        if existing is None or existing == "":
            ctx[key] = value
        elif isinstance(existing, list) and not existing:
            ctx[key] = value

    for idx, block in enumerate(layout):
        if not isinstance(block, dict):
            continue
        name = str(block.get("name") or "").strip()
        ctx = block.setdefault("context", {})
        if not isinstance(ctx, dict):
            ctx = {}
            block["context"] = ctx

        # 1) Generated per-element content for composite blocks (galleries, grids, …).
        if idx in bc:
            for key, value in bc[idx].items():
                _fill(ctx, key, value)

        if name == "header":
            _fill(ctx, "logo_text", company_name or "smart-letters")
            niche = str(company_profile.get("niche") or "").strip()
            _fill(ctx, "tagline", niche[:120] if niche else "Генерация email с ИИ")
            continue

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
            continue

        # 2) Generic top-level text/CTA fill for EVERY content block, based on the
        #    fields the block actually has. Fills only empty slots, so it never clobbers
        #    user-provided content or the per-element content injected above.
        fields = _block_fields(name)
        if subject and "title" in fields:
            _fill(ctx, "title", subject)
        if plain_body and "subtitle" in fields:
            _fill(ctx, "subtitle", plain_body[:280])
        if plain_body and "text" in fields:
            _fill(ctx, "text", plain_body[:400])
        if body_html and "paragraphs" in fields and not ctx.get("paragraphs"):
            ctx["paragraphs"] = [body_html]
        if subject and "caption" in fields:
            _fill(ctx, "caption", subject)
        if cta_label and "button_text" in fields:
            _fill(ctx, "button_text", cta_label)
        if cta_link and "button_url" in fields:
            _fill(ctx, "button_url", cta_link)
        # Image fields (top-level and nested) are filled at render time by
        # _apply_generated_images once the merged context is known.

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
    block_content: Optional[dict] = None,
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
        block_content=block_content,
    )
    builder = EmailBuilder(design=design)
    for block in layout:
        name = str(block.get("name") or "").strip()
        if not name:
            continue
        ctx = block.get("context")
        builder.add_block(name, ctx if isinstance(ctx, dict) else None)

    # With a real generated image available, replace every empty/placeholder image field
    # (including nested items of composite blocks) on the merged context so no example
    # "test" picture leaks into the final email. Previews (no image_url) keep examples.
    if image_url:
        alt = image_alt or subject or "Email image"
        for block in builder.blocks:
            _apply_generated_images(block.context, image_url, alt)

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
