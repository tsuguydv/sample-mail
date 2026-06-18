"""Specification and deterministic fallback content for composite (multi-item) blocks.

Generation fills only a handful of single-field blocks (hero/text/cta/image). Composite
blocks (gallery, product_grid, team, …) carry their content under list keys (or, for a
few blocks, as a single object) and otherwise render the registry's *example* placeholder
content — which the user perceives as leftover "test values".

This module describes the shape of that content so it can be generated (see
``generator.generate_block_content``) and provides a network-free fallback that fills every
required text field from the email subject/body while leaving media fields empty (the
renderer fills images with the generated picture).
"""
from __future__ import annotations

import re

# Each entry describes how to fill one block.
#   key:          list key holding items, or None for a single top-level object
#   count:        number of items to produce (matches the registry example length)
#   item_kind:    "object" (dict per item) or "string" (plain string per item)
#   text_fields:  fields the LLM/fallback must fill with text
#   image_fields: image URL fields the renderer fills (kept empty here)
#   alt_fields:   image alt-text fields (kept empty here; renderer fills from subject)
#   url_fields:   link fields (kept empty here; renderer/links handle them)
BLOCK_CONTENT_SPEC: dict[str, dict] = {
    "gallery": {
        "key": "items", "count": 3, "item_kind": "object",
        "text_fields": ["title"], "image_fields": ["image_url"], "alt_fields": ["image_alt"], "url_fields": [],
    },
    "product_grid": {
        "key": "products", "count": 3, "item_kind": "object",
        "text_fields": ["title", "price"], "image_fields": ["image_url"], "alt_fields": [], "url_fields": ["button_url"],
    },
    "team": {
        "key": "members", "count": 3, "item_kind": "object",
        "text_fields": ["name", "role"], "image_fields": ["image_url"], "alt_fields": [], "url_fields": [],
    },
    "article_list": {
        "key": "articles", "count": 3, "item_kind": "object",
        "text_fields": ["title", "text"], "image_fields": ["image_url"], "alt_fields": ["image_alt"], "url_fields": ["url"],
    },
    "benefits": {
        "key": "benefits", "count": 3, "item_kind": "object",
        "text_fields": ["title", "text"], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "feature_list": {
        "key": "items", "count": 4, "item_kind": "string",
        "text_fields": [], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "testimonials": {
        "key": "items", "count": 2, "item_kind": "object",
        "text_fields": ["quote", "author", "role"], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "pricing_table": {
        "key": "plans", "count": 3, "item_kind": "object",
        "text_fields": ["name", "price", "description", "button_text"], "image_fields": [], "alt_fields": [], "url_fields": ["button_url"],
    },
    "faq": {
        "key": "items", "count": 1, "item_kind": "object",
        "text_fields": ["question", "answer"], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "statistics": {
        "key": "stats", "count": 3, "item_kind": "object",
        "text_fields": ["value", "label"], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "timeline": {
        "key": "steps", "count": 3, "item_kind": "object",
        "text_fields": ["label", "title", "text"], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "icon_text": {
        "key": "items", "count": 2, "item_kind": "object",
        "text_fields": ["icon", "title", "text"], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "client_logos": {
        "key": "logos", "count": 4, "item_kind": "string",
        "text_fields": [], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    "service_card": {
        "key": "items", "count": 3, "item_kind": "string",
        "text_fields": [], "image_fields": [], "alt_fields": [], "url_fields": [],
    },
    # single-object blocks (no list key)
    "employee": {
        "key": None, "count": 1, "item_kind": "object",
        "text_fields": ["name", "role", "bio"], "image_fields": ["image_url"], "alt_fields": [], "url_fields": [],
    },
    "product_card": {
        "key": None, "count": 1, "item_kind": "object",
        "text_fields": ["title", "price", "button_text"], "image_fields": ["image_url"], "alt_fields": [], "url_fields": ["button_url"],
    },
}


def composite_blocks_in_layout(layout: list[dict] | None) -> list[tuple[int, str]]:
    """Indices and names of blocks in the layout that have a content spec."""
    out: list[tuple[int, str]] = []
    for idx, block in enumerate(layout or []):
        if not isinstance(block, dict):
            continue
        name = str(block.get("name") or "").strip()
        if name in BLOCK_CONTENT_SPEC:
            out.append((idx, name))
    return out


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def _sentences(body_html: str) -> list[str]:
    plain = _strip_html(body_html)
    parts = [s.strip() for s in re.split(r"(?<=[.!?])\s+", plain) if s.strip()]
    return parts


def _text_value(field: str, idx: int, *, subject: str, sentences: list[str]) -> str:
    """Pick a non-empty deterministic value for a text field."""
    subj = (subject or "").strip() or "Письмо"
    sent = sentences[idx % len(sentences)] if sentences else subj
    short = (sentences[0] if sentences else subj)[:48].strip() or subj
    mapping = {
        "title": f"{subj} — {idx + 1}" if idx else subj,
        "name": f"{subj} {idx + 1}",
        "label": str(idx + 1),
        "value": f"{(idx + 1) * 10}%",
        "price": "—",
        "icon": f"{idx + 1:02d}",
        "role": short,
        "author": f"{subj} {idx + 1}",
        "quote": sent,
        "text": sent,
        "answer": sent,
        "question": f"{subj}?",
        "bio": sent,
        "description": sent,
        "button_text": "Подробнее",
    }
    return mapping.get(field) or sent or subj


def _build_object_item(spec: dict, idx: int, *, subject: str, sentences: list[str]) -> dict:
    item: dict = {}
    for f in spec.get("text_fields", []):
        item[f] = _text_value(f, idx, subject=subject, sentences=sentences)
    for f in spec.get("image_fields", []) + spec.get("alt_fields", []) + spec.get("url_fields", []):
        item[f] = ""
    return item


def build_fallback_content(
    block_name: str,
    *,
    subject: str,
    body_html: str = "",
    language: str = "ru",
) -> dict:
    """Deterministic, network-free content of the right shape for ``block_name``.

    Every required text field is filled from the subject/body; media fields are left empty
    so the renderer can drop in the generated image. Guarantees the registry example is
    never used as a fallback.
    """
    spec = BLOCK_CONTENT_SPEC[block_name]
    sentences = _sentences(body_html)
    count = int(spec["count"])

    if spec["key"] is None:
        # single object at top level
        return _build_object_item(spec, 0, subject=subject, sentences=sentences)

    if spec["item_kind"] == "string":
        subj = (subject or "").strip() or "Пункт"
        items = [sentences[i] if i < len(sentences) else f"{subj} {i + 1}" for i in range(count)]
        return {spec["key"]: items}

    items = [_build_object_item(spec, i, subject=subject, sentences=sentences) for i in range(count)]
    return {spec["key"]: items}
