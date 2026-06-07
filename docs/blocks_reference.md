# Справочник блоков

Все блоки находятся в `templates/blocks/*.html`. CSS задан inline внутри HTML-шаблонов, а общие responsive-правила находятся в `templates/layout/base.html`. Такой подход выбран для совместимости с Gmail, Outlook, Apple Mail и Yahoo Mail: основа верстки построена на таблицах, без flex/grid, внешних шрифтов и JavaScript.

Примеры данных и описания параметров также зафиксированы в `email_builder/registry.py`, чтобы Python-код мог валидировать блоки и автоматически подставлять безопасные demo-значения.

## header

HTML: `templates/blocks/header.html`

CSS: inline-стили для таблицы шапки, текстового логотипа, подписи и ссылки веб-версии.

Параметры: `logo_text`, `tagline`, `view_url`, `view_text`.

Пример:

```python
{"logo_text": "Sample Mail", "tagline": "Email automation", "view_url": "#", "view_text": "Открыть в браузере"}
```

## hero

HTML: `templates/blocks/hero.html`

CSS: inline-стили для hero-изображения, типографики и bulletproof-кнопки.

Параметры: `eyebrow`, `title`, `subtitle`, `button_text`, `button_url`, `image_url`.

Пример:

```python
{"title": "Автоматизация email-маркетинга", "subtitle": "Собирайте персонализированные письма из модульных блоков.", "button_text": "Подробнее", "button_url": "#"}
```

## hero_split

HTML: `templates/blocks/hero_split.html`

CSS: table-based hero в две колонки, на мобильных колонки складываются.

Параметры: `eyebrow`, `title`, `subtitle`, `button_text`, `button_url`, `image_url`, `image_alt`.

Пример:

```python
{"eyebrow": "Новый формат", "title": "Письмо с визуальным акцентом", "subtitle": "Двухколоночный hero для продуктовых писем.", "button_text": "Открыть", "button_url": "#", "image_url": "https://via.placeholder.com/260x220", "image_alt": "Preview"}
```

## hero_compact

HTML: `templates/blocks/hero_compact.html`

CSS: компактный цветной баннер без изображения.

Параметры: `eyebrow`, `title`, `subtitle`, `button_text`, `button_url`.

Пример:

```python
{"eyebrow": "Объявление", "title": "Важное обновление", "subtitle": "Короткий формат для быстрых писем.", "button_text": "Подробнее", "button_url": "#"}
```

## text

HTML: `templates/blocks/text.html`

CSS: inline-стили для заголовка и абзацев.

Параметры: `title`, `paragraphs`.

Пример:

```python
{"title": "Почему это важно", "paragraphs": ["Модульная структура ускоряет выпуск рассылок."]}
```

## text_quote

HTML: `templates/blocks/text_quote.html`

CSS: цитата с цветовой линией слева и светлым фоном.

Параметры: `quote`, `author`, `role`.

Пример:

```python
{"quote": "Модульные письма помогли тестировать гипотезы быстрее.", "author": "Анна Петрова", "role": "CMO"}
```

## image_left

HTML: `templates/blocks/image_left.html`

CSS: table-based две колонки, mobile stacking через классы из `base.html`.

Параметры: `image_url`, `image_alt`, `title`, `text`, `button_text`, `button_url`.

Пример:

```python
{"image_url": "https://via.placeholder.com/260x180", "image_alt": "Feature", "title": "Быстрый запуск", "text": "Соберите письмо из готовых блоков.", "button_text": "Посмотреть", "button_url": "#"}
```

## image_right

HTML: `templates/blocks/image_right.html`

CSS: table-based две колонки, зеркальная композиция.

Параметры: `image_url`, `image_alt`, `title`, `text`, `button_text`, `button_url`.

Пример:

```python
{"image_url": "https://via.placeholder.com/260x180", "image_alt": "Workflow", "title": "Единый процесс", "text": "Контент управляется через параметры.", "button_text": "Узнать больше", "button_url": "#"}
```

## image_full

HTML: `templates/blocks/image_full.html`

CSS: inline-стили для fluid image и подписи.

Параметры: `image_url`, `image_alt`, `caption`.

Пример:

```python
{"image_url": "https://via.placeholder.com/600x280", "image_alt": "Campaign", "caption": "Баннер кампании"}
```

## gallery

HTML: `templates/blocks/gallery.html`

CSS: табличная сетка из трех колонок с адаптивным stacking.

Параметры: `items`, где каждый элемент содержит `image_url`, `image_alt`, `title`.

Пример:

```python
{"items": [{"image_url": "https://via.placeholder.com/180x140", "image_alt": "One", "title": "Сегменты"}]}
```

## article_list

HTML: `templates/blocks/article_list.html`

CSS: вертикальный список материалов с миниатюрами.

Параметры: `title`, `articles`, где каждый элемент содержит `image_url`, `image_alt`, `title`, `text`, `url`.

Пример:

```python
{"title": "Полезные материалы", "articles": [{"image_url": "https://via.placeholder.com/88x66", "image_alt": "Article", "title": "Как проектировать блоки", "text": "Короткое описание.", "url": "#"}]}
```

## video_preview

HTML: `templates/blocks/video_preview.html`

CSS: inline-стили превью-изображения и ссылки на видео.

Параметры: `image_url`, `image_alt`, `title`, `button_text`, `button_url`.

Пример:

```python
{"image_url": "https://via.placeholder.com/600x300", "image_alt": "Video", "title": "Посмотрите обзор", "button_text": "Смотреть", "button_url": "#"}
```

## cta

HTML: `templates/blocks/cta.html`

CSS: border-card таблица и bulletproof-кнопка.

Параметры: `title`, `text`, `button_text`, `button_url`.

Пример:

```python
{"title": "Готовы начать?", "text": "Запустите первую кампанию.", "button_text": "Начать", "button_url": "#"}
```

## cta_banner

HTML: `templates/blocks/cta_banner.html`

CSS: акцентная таблица с фоновым цветом и белой кнопкой.

Параметры: `title`, `text`, `button_text`, `button_url`.

Пример:

```python
{"title": "Персональные рассылки быстрее", "text": "Используйте готовые блоки.", "button_text": "Попробовать", "button_url": "#"}
```

## benefits

HTML: `templates/blocks/benefits.html`

CSS: три табличные карточки с адаптивным stacking.

Параметры: `title`, `benefits`, где каждый элемент содержит `title`, `text`.

Пример:

```python
{"title": "Преимущества", "benefits": [{"title": "Модульность", "text": "Блоки легко комбинировать."}]}
```

## feature_list

HTML: `templates/blocks/feature_list.html`

CSS: bordered table-card со списком пунктов и текстовыми отметками.

Параметры: `title`, `items`.

Пример:

```python
{"title": "Что можно сделать", "items": ["Собрать письмо из блоков.", "Переиспользовать шаблоны."]}
```

## icon_text

HTML: `templates/blocks/icon_text.html`

CSS: таблица с круглым текстовым маркером и описанием.

Параметры: `items`, где каждый элемент содержит `icon`, `title`, `text`.

Пример:

```python
{"items": [{"icon": "01", "title": "Сегментация", "text": "Разные блоки для разных аудиторий."}]}
```

## statistics

HTML: `templates/blocks/statistics.html`

CSS: табличная сетка показателей на светлом фоне.

Параметры: `stats`, где каждый элемент содержит `value`, `label`.

Пример:

```python
{"stats": [{"value": "32%", "label": "рост CTR"}]}
```

## social_proof

HTML: `templates/blocks/social_proof.html`

CSS: компактный блок доверия с текстом и крупной метрикой.

Параметры: `title`, `text`, `metric`, `metric_label`.

Пример:

```python
{"title": "Команды быстрее выпускают кампании", "text": "Модульная структура снижает ручную работу.", "metric": "2.4x", "metric_label": "ускорение запуска"}
```

## testimonials

HTML: `templates/blocks/testimonials.html`

CSS: две табличные карточки отзывов.

Параметры: `title`, `items`, где каждый элемент содержит `quote`, `author`, `role`.

Пример:

```python
{"title": "Отзывы", "items": [{"quote": "Стали выпускать быстрее.", "author": "Анна", "role": "CMO"}]}
```

## case_study

HTML: `templates/blocks/case_study.html`

CSS: таблица с цветовой линией слева и акцентным результатом.

Параметры: `label`, `title`, `text`, `result`.

Пример:

```python
{"label": "Кейс", "title": "Рост кампаний", "text": "Команда перешла на блоки.", "result": "+28% к конверсии"}
```

## client_logos

HTML: `templates/blocks/client_logos.html`

CSS: табличная сетка текстовых логотипов.

Параметры: `title`, `logos`.

Пример:

```python
{"title": "Нам доверяют", "logos": ["Northwind", "Contoso", "Fabrikam", "Globex"]}
```

## team

HTML: `templates/blocks/team.html`

CSS: табличная сетка сотрудников с круглыми изображениями.

Параметры: `title`, `members`, где каждый элемент содержит `name`, `role`, `image_url`.

Пример:

```python
{"title": "Команда", "members": [{"name": "Мария", "role": "Strategist", "image_url": "https://via.placeholder.com/120"}]}
```

## employee

HTML: `templates/blocks/employee.html`

CSS: горизонтальная табличная карточка сотрудника.

Параметры: `name`, `role`, `bio`, `image_url`.

Пример:

```python
{"name": "Дмитрий Иванов", "role": "Руководитель продукта", "bio": "Помогает запускать кампании.", "image_url": "https://via.placeholder.com/128"}
```

## product_card

HTML: `templates/blocks/product_card.html`

CSS: карточка товара с изображением, ценой и ссылкой.

Параметры: `title`, `price`, `image_url`, `button_text`, `button_url`.

Пример:

```python
{"title": "Email-пакет Pro", "price": "4 900 ₽", "image_url": "https://via.placeholder.com/520x260", "button_text": "Купить", "button_url": "#"}
```

## product_grid

HTML: `templates/blocks/product_grid.html`

CSS: табличная сетка товаров с адаптивным stacking.

Параметры: `title`, `products`, где каждый элемент содержит `title`, `price`, `image_url`, `button_url`.

Пример:

```python
{"title": "Популярные товары", "products": [{"title": "Starter", "price": "990 ₽", "image_url": "https://via.placeholder.com/180x140", "button_url": "#"}]}
```

## pricing_table

HTML: `templates/blocks/pricing_table.html`

CSS: три табличные карточки тарифов с адаптивным stacking.

Параметры: `title`, `plans`, где каждый элемент содержит `name`, `price`, `description`, `button_text`, `button_url`.

Пример:

```python
{"title": "Выберите пакет", "plans": [{"name": "Starter", "price": "990 ₽", "description": "Для первых кампаний.", "button_text": "Выбрать", "button_url": "#"}]}
```

## service_card

HTML: `templates/blocks/service_card.html`

CSS: bordered table-card со списком пунктов.

Параметры: `title`, `text`, `items`, `button_text`, `button_url`.

Пример:

```python
{"title": "Внедрение", "text": "Соберем библиотеку блоков.", "items": ["Аудит", "Дизайн"], "button_text": "Обсудить", "button_url": "#"}
```

## faq

HTML: `templates/blocks/faq.html`

CSS: список вопросов с разделителями.

Параметры: `title`, `items`, где каждый элемент содержит `question`, `answer`.

Пример:

```python
{"title": "Вопросы", "items": [{"question": "Можно ли добавлять блоки?", "answer": "Да."}]}
```

## timeline

HTML: `templates/blocks/timeline.html`

CSS: вертикальный список шагов с круглыми номерами.

Параметры: `title`, `steps`, где каждый элемент содержит `label`, `title`, `text`.

Пример:

```python
{"title": "План запуска", "steps": [{"label": "1", "title": "Выбор блоков", "text": "Определяем структуру."}]}
```

## promo

HTML: `templates/blocks/promo.html`

CSS: промо-таблица с крупным процентом скидки и CTA-ссылкой.

Параметры: `discount`, `title`, `text`, `code`, `button_text`, `button_url`.

Пример:

```python
{"discount": "-30%", "title": "Специальное предложение", "text": "До конца недели.", "code": "EMAIL30", "button_text": "Получить", "button_url": "#"}
```

## coupon

HTML: `templates/blocks/coupon.html`

CSS: купон с dashed border, промокодом и ссылкой.

Параметры: `label`, `title`, `text`, `code`, `button_text`, `button_url`.

Пример:

```python
{"label": "Персональный бонус", "title": "Сохраните промокод", "text": "Используйте его при заказе.", "code": "MAIL20", "button_text": "Применить", "button_url": "#"}
```

## divider

HTML: `templates/blocks/divider.html`

CSS: табличный горизонтальный разделитель.

Параметры: нет.

Пример:

```python
{}
```

## spacer

HTML: `templates/blocks/spacer.html`

CSS: табличный вертикальный отступ.

Параметры: `height`.

Пример:

```python
{"height": 16}
```

## footer

HTML: `templates/blocks/footer.html`

CSS: inline-стили подвала, ссылок и unsubscribe-текста.

Параметры: `company_name`, `address`, `unsubscribe_url`, `unsubscribe_text`, `social_links`.

Пример:

```python
{"company_name": "Sample Mail", "address": "Екатеринбург, Россия", "unsubscribe_url": "#", "unsubscribe_text": "Отписаться", "social_links": [{"title": "Website", "url": "#"}]}
```
