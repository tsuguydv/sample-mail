"""
Template rendering system for email templates.
Uses Jinja2 to populate HTML templates with user data.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Get the templates directory path
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml']),
    trim_blocks=True,
    lstrip_blocks=True
)

def get_color_scheme(color_scheme: Optional[str], primary_color: str = "#4f46e5") -> Dict[str, str]:
    """
    Get color values based on the selected color scheme.
    Returns a dict with primary_color, secondary_color, header_bg_color, text_color.
    """
    schemes = {
        "light": {
            "primary_color": "#4f46e5",
            "secondary_color": "#7c3aed",
            "header_bg_color": "#ffffff",
            "text_color": "#1f2937",
        },
        "dark": {
            "primary_color": "#6366f1",
            "secondary_color": "#8b5cf6",
            "header_bg_color": "#1f2937",
            "text_color": "#f9fafb",
        },
        "brand": {
            "primary_color": primary_color,
            "secondary_color": primary_color,
            "header_bg_color": "#f8f9fa",
            "text_color": "#212529",
        },
    }
    
    return schemes.get(color_scheme or "light", schemes["light"])


def render_social_links(socials: Optional[str]) -> str:
    """
    Convert comma-separated social media links into HTML.
    """
    if not socials:
        return ""
    
    links = [link.strip() for link in socials.split(",") if link.strip()]
    if not links:
        return ""
    
    html_parts = []
    for link in links:
        # Simple social link rendering
        html_parts.append(
            f'<a href="{link}" style="display: inline-block; margin: 0 8px; color: #666666; text-decoration: none; font-size: 12px;">🔗</a>'
        )
    
    return " ".join(html_parts)


def render_template(
    template_id: str,
    company_profile: Dict[str, Any],
    subject: str,
    body_html: str,
    image_url: Optional[str] = None,
    image_alt: Optional[str] = None,
    cta_link: Optional[str] = None,
    cta_label: Optional[str] = None,
    color_scheme: Optional[str] = None,
    language: str = "ru",
    template_config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render an email template with the provided data.
    
    Args:
        template_id: Template identifier (t1, t2, t3)
        company_profile: Company information dict
        subject: Email subject
        body_html: Email body HTML content
        image_url: Optional image URL
        image_alt: Optional image alt text
        cta_link: Optional CTA button link
        cta_label: Optional CTA button label
        color_scheme: Optional color scheme (light, dark, brand)
        language: Language code (ru, en)
    
    Returns:
        Rendered HTML email as string
    """
    # Map template IDs to template files
    template_files = {
        "t1": "t1_classic.html",
        "t2": "t2_minimalist.html",
        "t3": "t3_bright_cta.html",
        "t4": "t4_modern_card.html",
    }
    
    cfg = template_config or {}
    theme_cfg = cfg.get("theme") if isinstance(cfg, dict) else {}
    if not isinstance(theme_cfg, dict):
        theme_cfg = {}
    style_key = str(theme_cfg.get("style", "")).strip().lower()
    style_to_file = {
        "classic": "t1_classic.html",
        "minimal": "t2_minimalist.html",
        "bright": "t3_bright_cta.html",
        "modern": "t4_modern_card.html",
    }
    template_file = style_to_file.get(style_key) or template_files.get(template_id, "t1_classic.html")
    template = env.get_template(template_file)
    
    # Get color scheme
    colors = get_color_scheme(color_scheme)
    
    # Shared template components for future builder support.
    company_name = company_profile.get("companyName", "")
    logo = company_profile.get("logoUrl")
    company_email = company_profile.get("email")
    company_phone = company_profile.get("phone")
    company_website = company_profile.get("website")
    # Social rendering is disabled for now.
    social_links = ""
    heading_text = subject or company_name or ""

    blocks_cfg = cfg.get("blocks") if isinstance(cfg, dict) else None
    if not isinstance(blocks_cfg, list):
        blocks_cfg = []
    known_block_types = ("heading", "logo", "image", "body", "cta", "footer")
    # If a block type is missing from config, treat it as disabled.
    # This makes builder remove/toggle actions affect final rendering.
    block_enabled = {k: False for k in known_block_types}
    block_props = {}
    for b in blocks_cfg:
        if isinstance(b, dict):
            btype = str(b.get("type") or b.get("id") or "").strip().lower()
            if btype:
                enabled = bool(b.get("enabled", True))
                block_enabled[btype] = block_enabled.get(btype, False) or enabled
                block_props.setdefault(btype, {})
                props = b.get("props")
                if isinstance(props, dict):
                    block_props[btype].update(props)

    def p(name: str, key: str, default: Any) -> Any:
        return block_props.get(name, {}).get(key, default)

    raw_font_size = p("body", "fontSize", 16)
    try:
        body_font_size = int(raw_font_size)
    except (TypeError, ValueError):
        body_font_size = 16

    components = {
        "heading": {
            "text": heading_text,
            "companyName": company_name,
            "align": p("heading", "align", "left"),
            "textColor": p("heading", "textColor", colors["text_color"]),
            "backgroundColor": p("heading", "backgroundColor", colors["header_bg_color"]),
        },
        "theme": {
            "colorScheme": color_scheme or "light",
            "primary": str(theme_cfg.get("primary") or colors["primary_color"]),
            "secondary": str(theme_cfg.get("secondary") or colors["secondary_color"]),
            "headerBg": colors["header_bg_color"],
            "text": colors["text_color"],
        },
        "logo": {
            "url": logo,
            "alt": company_name or "Company logo",
            "enabled": bool(logo) and block_enabled.get("logo", False),
            "align": p("logo", "align", "left"),
            "size": p("logo", "size", "md"),
        },
        "media": {
            "imageUrl": image_url,
            "imageAlt": image_alt or "Email image",
            "hasImage": bool(image_url) and block_enabled.get("image", False),
            "align": p("image", "align", "center"),
            "rounded": bool(p("image", "rounded", True)),
        },
        "body": {
            "html": body_html,
            "enabled": block_enabled.get("body", False),
            "align": p("body", "align", "left"),
            "textColor": p("body", "textColor", colors["text_color"]),
            "backgroundColor": p("body", "backgroundColor", "#ffffff"),
            "fontSize": body_font_size,
        },
        "cta": {
            "link": cta_link,
            "label": cta_label,
            "enabled": bool(cta_link) and block_enabled.get("cta", False),
            "align": p("cta", "align", "center"),
            "textColor": p("cta", "textColor", "#ffffff"),
            "backgroundColor": p("cta", "backgroundColor", str(theme_cfg.get("primary") or colors["primary_color"])),
            "style": p("cta", "style", "solid"),
        },
        "footer": {
            "companyName": company_name or "",
            "email": company_email,
            "phone": company_phone,
            "website": company_website,
            "socialLinksHtml": "",
            "hasSocialLinks": False,
            "enabled": block_enabled.get("footer", False),
            "align": p("footer", "align", "left"),
            "textColor": p("footer", "textColor", "#666666"),
            "backgroundColor": p("footer", "backgroundColor", "#f8f9fa"),
        },
    }

    # Prepare template context (components + legacy flat keys for compatibility)
    context = {
        "language": language,
        "subject": subject,
        "components": components,
        "company_name": company_name,
        "logo_url": logo,
        "company_email": company_email,
        "company_phone": company_phone,
        "company_website": company_website,
        "social_links": social_links,
        "body_html": body_html,
        "image_url": image_url,
        "image_alt": image_alt or "Email image",
        "cta_link": cta_link,
        "cta_label": cta_label,
        **colors,  # Add all color variables
    }
    
    # Render the template
    return template.render(**context)
