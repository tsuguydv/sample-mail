from app import block_content as bc
from app.email_builder.registry import get_block_example


def test_spec_keys_match_registry_examples():
    # для блоков со списком (key != None) ключ должен присутствовать в примере реестра
    for name, spec in bc.BLOCK_CONTENT_SPEC.items():
        if spec["key"] is None:
            continue
        ex = get_block_example(name)
        assert spec["key"] in ex, f"{name}: ключ {spec['key']} отсутствует в примере"


def test_composite_blocks_in_layout():
    layout = [{"name": "header"}, {"name": "gallery"}, {"name": "text"}, {"name": "team"}]
    assert bc.composite_blocks_in_layout(layout) == [(1, "gallery"), (3, "team")]


def test_fallback_fills_required_shape_no_placeholders():
    out = bc.build_fallback_content(
        "gallery", subject="Запуск", body_html="<p>Текст письма тут.</p>", language="ru"
    )
    assert isinstance(out["items"], list) and len(out["items"]) == 3
    for it in out["items"]:
        assert it["title"]                      # текст заполнен
        assert it.get("image_url", "") == ""    # картинка пустая (заполнит рендер)

    fl = bc.build_fallback_content(
        "feature_list", subject="Запуск", body_html="<p>a</p><p>b</p>", language="ru"
    )
    assert all(isinstance(s, str) and s for s in fl["items"])


def test_fallback_all_blocks_text_filled_media_empty():
    for name, spec in bc.BLOCK_CONTENT_SPEC.items():
        out = bc.build_fallback_content(
            name, subject="Тема письма", body_html="<p>Первое.</p><p>Второе предложение.</p>", language="ru"
        )
        media_fields = spec.get("image_fields", []) + spec.get("alt_fields", []) + spec.get("url_fields", [])

        if spec["key"] is None:
            # одиночный объект — поля на верхнем уровне
            for f in spec.get("text_fields", []):
                assert out.get(f), f"{name}.{f} пустое"
            for f in media_fields:
                assert out.get(f, "") == "", f"{name}.{f} должно быть пустым"
            continue

        items = out[spec["key"]]
        assert isinstance(items, list) and len(items) == spec["count"]
        if spec["item_kind"] == "string":
            assert all(isinstance(s, str) and s for s in items)
            continue
        for it in items:
            for f in spec.get("text_fields", []):
                assert it.get(f), f"{name}.{f} пустое"
            for f in media_fields:
                assert it.get(f, "") == "", f"{name}.{f} должно быть пустым"
