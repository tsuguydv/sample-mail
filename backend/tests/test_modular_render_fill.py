import re

from app.modular_renderer import render_modular_email

LAYOUT_TEST = [
    {"name": n, "context": {}} for n in ["header", "hero", "hero_split", "text", "cta", "footer"]
]


def test_no_placeholder_when_image_provided():
    html = render_modular_email(
        LAYOUT_TEST,
        company_profile={"companyName": "Акме"},
        subject="Запуск",
        body_html="<p>Текст письма.</p>",
        image_url="https://r2.example/REAL.jpg",
        image_alt="x",
        cta_link="https://acme.io",
        cta_label="Купить",
    )
    assert not re.search(r"via\.placeholder\.com|placehold\.co", html)
    assert html.count("REAL.jpg") >= 2  # и hero, и hero_split


def test_block_content_text_used_for_composite():
    layout = [
        {"name": "header", "context": {}},
        {"name": "gallery", "context": {}},
        {"name": "footer", "context": {}},
    ]
    bc = {1: {"items": [{"title": f"Слайд {i}", "image_alt": "", "image_url": ""} for i in range(3)]}}
    html = render_modular_email(
        layout,
        company_profile={},
        subject="S",
        image_url="https://r2.example/REAL.jpg",
        block_content=bc,
    )
    assert "Слайд 1" in html
    assert not re.search(r"via\.placeholder\.com|placehold\.co", html)
    assert html.count("REAL.jpg") >= 3  # 3 слота галереи


def test_preview_without_image_keeps_examples():
    html = render_modular_email(LAYOUT_TEST, company_profile={}, subject="S")  # image_url=None
    assert "placehold.co" in html or "via.placeholder.com" in html
