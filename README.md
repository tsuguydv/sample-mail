# Sample Mail: модульный конструктор HTML email-писем

Проект реализует production-ready основу для сборки HTML email-рассылок из независимых Jinja2-блоков. ML-часть намеренно не реализована: текущая архитектура готовит структурированные блоки, которые позже можно выбирать или персонализировать алгоритмами машинного обучения.

## Структура проекта

```text
sample-mail/
├── email_builder/
│   ├── __init__.py
│   ├── builder.py
│   ├── models.py
│   └── registry.py
├── templates/
│   ├── layout/
│   │   └── base.html
│   └── blocks/
│       ├── header.html
│       ├── hero.html
│       ├── hero_split.html
│       ├── hero_compact.html
│       ├── text.html
│       ├── text_quote.html
│       ├── image_left.html
│       ├── image_right.html
│       ├── image_full.html
│       ├── gallery.html
│       ├── article_list.html
│       ├── video_preview.html
│       ├── cta.html
│       ├── cta_banner.html
│       ├── benefits.html
│       ├── feature_list.html
│       ├── icon_text.html
│       ├── statistics.html
│       ├── social_proof.html
│       ├── testimonials.html
│       ├── case_study.html
│       ├── client_logos.html
│       ├── team.html
│       ├── employee.html
│       ├── product_card.html
│       ├── product_grid.html
│       ├── pricing_table.html
│       ├── service_card.html
│       ├── faq.html
│       ├── timeline.html
│       ├── promo.html
│       ├── coupon.html
│       ├── divider.html
│       ├── spacer.html
│       └── footer.html
├── examples/
│   ├── generate_examples.py
│   └── sample_emails.py
├── docs/
│   └── blocks_reference.md
├── output/
├── main.py
├── README.md
└── requirements.txt
```

## Архитектура

`EmailBuilder` хранит список блоков письма и отвечает за четыре операции: `add_block()`, `remove_block()`, `clear()`, `render()`.

Каждый блок является отдельным HTML-шаблоном в `templates/blocks`. Общий каркас письма находится в `templates/layout/base.html`; builder рендерит блоки по очереди и автоматически передает их в `base.html` через переменную `blocks`.

`email_builder/registry.py` содержит реестр доступных блоков, описание параметров и пример данных для каждого блока. При добавлении блока builder валидирует имя и подмешивает demo-значения, поэтому минимальный запуск остается удобным, а недостающие параметры не ломают примерные письма.

## Email-совместимость

Шаблоны ориентированы на Gmail, Outlook, Apple Mail и Yahoo Mail:

- table-based layout;
- inline CSS внутри блоков;
- простые media queries в `base.html`;
- без JavaScript, flexbox, CSS grid, web fonts и сложных CSS-селекторов;
- изображения имеют `alt`, фиксированные `width` и адаптивное поведение через класс `fluid-img`.

## Быстрый старт

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Результат будет сохранен в `output/email.html`.

## Пример использования

```python
from email_builder import EmailBuilder

builder = EmailBuilder()

builder.add_block(
    "hero",
    {
        "title": "Автоматизация email-маркетинга",
        "subtitle": "Увеличьте продажи",
        "button_text": "Подробнее",
        "button_url": "#",
    },
)

builder.add_block("benefits")
builder.add_block("footer")

html = builder.render({"preheader": "Письмо собрано из модульных блоков"})
```

## Готовые примеры писем

В `examples/sample_emails.py` реализованы:

- B2B SaaS;
- интернет-магазин;
- корпоративное письмо;
- акционная рассылка;
- welcome email.
- запуск продукта;
- приглашение на вебинар;
- еженедельный дайджест;
- письмо о брошенной корзине;
- реактивационная рассылка;
- onboarding email;
- письмо с кейсом;
- коммерческое предложение услуги.

Сгенерировать все примеры можно командой:

```bash
python -m examples.generate_examples
```

HTML-файлы будут созданы в `output/examples`. Генератор не удаляет и не перезаписывает старые письма: если файл с таким именем уже существует, новое письмо будет сохранено с суффиксом `_001`, `_002` и так далее.

## Вариации блоков

В библиотеку входят базовые блоки и альтернативные варианты для разных сценариев:

- hero-варианты: `hero`, `hero_split`, `hero_compact`;
- контент: `text`, `text_quote`, `article_list`, `gallery`, `video_preview`;
- преимущества и доверие: `benefits`, `feature_list`, `icon_text`, `statistics`, `social_proof`, `testimonials`, `case_study`, `client_logos`;
- коммерческие блоки: `product_card`, `product_grid`, `pricing_table`, `service_card`, `promo`, `coupon`, `cta`, `cta_banner`;
- служебные блоки: `header`, `footer`, `divider`, `spacer`.

## Добавление нового блока

1. Создайте HTML-шаблон в `templates/blocks/new_block.html`.
2. Используйте table-based layout и inline CSS.
3. Добавьте метаданные блока в `BLOCK_REGISTRY` в `email_builder/registry.py`.
4. Передавайте блок через `builder.add_block("new_block", {...})`.

Такой контракт оставляет систему расширяемой: ML-модуль в будущем сможет работать не с произвольным HTML, а с типизированными именами блоков и структурированными параметрами.
