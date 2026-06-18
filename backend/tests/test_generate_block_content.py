import json

from app import generator


def test_returns_empty_when_no_composite():
    layout = [{"name": "header"}, {"name": "hero"}, {"name": "text"}, {"name": "footer"}]
    assert generator.generate_block_content(layout=layout, company_profile={}, subject="x") == {}


def test_fallback_on_llm_error(monkeypatch):
    layout = [{"name": "gallery"}, {"name": "benefits"}]

    def boom(*a, **k):
        raise RuntimeError("no llm")

    monkeypatch.setattr(generator, "_llm_chat", boom)
    out = generator.generate_block_content(
        layout=layout, company_profile={"companyName": "Акме"}, subject="Запуск", body_html="<p>Текст.</p>"
    )
    assert set(out.keys()) == {0, 1}
    assert len(out[0]["items"]) == 3 and out[0]["items"][0]["title"]
    assert len(out[1]["benefits"]) == 3


def test_uses_llm_output_and_clears_media(monkeypatch):
    layout = [{"name": "gallery"}]

    def fake_chat(messages, temperature=0.3):
        return json.dumps({
            "0": {"items": [
                {"title": "Слайд A", "image_url": "https://via.placeholder.com/1", "image_alt": "x"},
                {"title": "Слайд B", "image_url": "http://example/2.png", "image_alt": "y"},
                {"title": "Слайд C", "image_url": "", "image_alt": ""},
            ]}
        }, ensure_ascii=False)

    monkeypatch.setattr(generator, "_llm_chat", fake_chat)
    out = generator.generate_block_content(layout=layout, company_profile={}, subject="S", body_html="<p>a</p>")
    items = out[0]["items"]
    assert [it["title"] for it in items] == ["Слайд A", "Слайд B", "Слайд C"]
    # media-поля принудительно очищены (заполнит рендер)
    assert all(it["image_url"] == "" for it in items)
