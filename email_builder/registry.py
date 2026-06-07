from __future__ import annotations

from copy import deepcopy

from .models import BlockMetadata, Context


DESIGN_DEFAULTS: Context = {
    "brand_name": "Sample Mail",
    "brand_url": "#",
    "preheader": "Новое письмо от Sample Mail",
    "background_color": "#f3f6fb",
    "surface_color": "#ffffff",
    "primary_color": "#246bfe",
    "primary_dark": "#1749b5",
    "accent_color": "#11a683",
    "text_color": "#172033",
    "muted_color": "#5f6f89",
    "border_color": "#dfe7f3",
    "font_family": "Arial, Helvetica, sans-serif",
    "container_width": 640,
}


BLOCK_REGISTRY: dict[str, BlockMetadata] = {
    "header": BlockMetadata(
        "header",
        "Шапка письма с логотипом, короткой подписью и ссылкой.",
        {
            "logo_text": "Текстовый логотип или название бренда.",
            "tagline": "Короткая подпись рядом с брендом.",
            "view_url": "Ссылка на веб-версию письма.",
            "view_text": "Текст ссылки на веб-версию.",
        },
        {
            "logo_text": "Sample Mail",
            "tagline": "Email automation",
            "view_url": "#",
            "view_text": "Открыть в браузере",
        },
    ),
    "hero": BlockMetadata(
        "hero",
        "Главный экран письма с заголовком, подзаголовком и CTA.",
        {
            "eyebrow": "Надзаголовок.",
            "title": "Основной заголовок.",
            "subtitle": "Подзаголовок.",
            "button_text": "Текст кнопки.",
            "button_url": "URL кнопки.",
            "image_url": "Опциональное изображение.",
        },
        {
            "eyebrow": "Новая платформа",
            "title": "Автоматизация email-маркетинга",
            "subtitle": "Собирайте персонализированные письма из модульных блоков.",
            "button_text": "Подробнее",
            "button_url": "#",
            "image_url": "https://via.placeholder.com/560x240/246BFE/FFFFFF?text=Email+Builder",
        },
    ),
    "text": BlockMetadata(
        "text",
        "Текстовый блок с заголовком и абзацами.",
        {"title": "Заголовок.", "paragraphs": "Список абзацев."},
        {
            "title": "Почему это важно",
            "paragraphs": [
                "Модульная структура ускоряет выпуск рассылок и снижает количество ручной работы.",
                "Каждый блок можно переиспользовать и позже выбирать алгоритмами ML.",
            ],
        },
    ),
    "hero_split": BlockMetadata(
        "hero_split",
        "Главный экран в две колонки: текст и изображение.",
        {
            "eyebrow": "Надзаголовок.",
            "title": "Основной заголовок.",
            "subtitle": "Подзаголовок.",
            "button_text": "Текст кнопки.",
            "button_url": "URL кнопки.",
            "image_url": "URL изображения.",
            "image_alt": "Alt-текст.",
        },
        {
            "eyebrow": "Новый формат",
            "title": "Письмо с визуальным акцентом",
            "subtitle": "Двухколоночный hero подходит для продуктовых и onboarding-рассылок.",
            "button_text": "Открыть",
            "button_url": "#",
            "image_url": "https://via.placeholder.com/260x220/246BFE/FFFFFF?text=Preview",
            "image_alt": "Preview",
        },
    ),
    "hero_compact": BlockMetadata(
        "hero_compact",
        "Компактный hero-баннер без изображения.",
        {
            "eyebrow": "Надзаголовок.",
            "title": "Основной заголовок.",
            "subtitle": "Подзаголовок.",
            "button_text": "Текст ссылки.",
            "button_url": "URL ссылки.",
        },
        {
            "eyebrow": "Короткое объявление",
            "title": "Важное обновление для вашей команды",
            "subtitle": "Компактный блок экономит место и хорошо работает в коротких письмах.",
            "button_text": "Подробнее",
            "button_url": "#",
        },
    ),
    "text_quote": BlockMetadata(
        "text_quote",
        "Цитата или выделенный отзыв в текстовом формате.",
        {"quote": "Текст цитаты.", "author": "Автор.", "role": "Роль или должность."},
        {
            "quote": "Модульные письма помогли нам тестировать гипотезы быстрее и аккуратнее.",
            "author": "Анна Петрова",
            "role": "CMO",
        },
    ),
    "image_left": BlockMetadata(
        "image_left",
        "Двухколоночный блок: изображение слева, текст справа.",
        {
            "image_url": "URL изображения.",
            "image_alt": "Alt-текст.",
            "title": "Заголовок.",
            "text": "Описание.",
            "button_text": "Текст ссылки.",
            "button_url": "URL ссылки.",
        },
        {
            "image_url": "https://via.placeholder.com/260x180/11A683/FFFFFF?text=Feature",
            "image_alt": "Feature",
            "title": "Быстрый запуск",
            "text": "Соберите письмо из готовых блоков без верстки с нуля.",
            "button_text": "Посмотреть",
            "button_url": "#",
        },
    ),
    "image_right": BlockMetadata(
        "image_right",
        "Двухколоночный блок: текст слева, изображение справа.",
        {
            "image_url": "URL изображения.",
            "image_alt": "Alt-текст.",
            "title": "Заголовок.",
            "text": "Описание.",
            "button_text": "Текст ссылки.",
            "button_url": "URL ссылки.",
        },
        {
            "image_url": "https://via.placeholder.com/260x180/246BFE/FFFFFF?text=Workflow",
            "image_alt": "Workflow",
            "title": "Единый процесс",
            "text": "Контент, дизайн и структура письма управляются через параметры.",
            "button_text": "Узнать больше",
            "button_url": "#",
        },
    ),
    "image_full": BlockMetadata(
        "image_full",
        "Полноширинное изображение с подписью.",
        {"image_url": "URL изображения.", "image_alt": "Alt-текст.", "caption": "Подпись."},
        {
            "image_url": "https://via.placeholder.com/600x280/172033/FFFFFF?text=Campaign",
            "image_alt": "Campaign",
            "caption": "Пример визуального баннера кампании.",
        },
    ),
    "gallery": BlockMetadata(
        "gallery",
        "Галерея из трех изображений.",
        {"items": "Список объектов image_url, image_alt, title."},
        {
            "items": [
                {"image_url": "https://via.placeholder.com/180x140/246BFE/FFFFFF?text=1", "image_alt": "One", "title": "Сегменты"},
                {"image_url": "https://via.placeholder.com/180x140/11A683/FFFFFF?text=2", "image_alt": "Two", "title": "Шаблоны"},
                {"image_url": "https://via.placeholder.com/180x140/172033/FFFFFF?text=3", "image_alt": "Three", "title": "Отчеты"},
            ]
        },
    ),
    "article_list": BlockMetadata(
        "article_list",
        "Список статей или материалов дайджеста.",
        {"title": "Заголовок секции.", "articles": "Список объектов image_url, image_alt, title, text, url."},
        {
            "title": "Полезные материалы",
            "articles": [
                {
                    "image_url": "https://via.placeholder.com/88x66/246BFE/FFFFFF?text=A1",
                    "image_alt": "Article 1",
                    "title": "Как проектировать блоки для email",
                    "text": "Короткий практический материал о структуре шаблонов.",
                    "url": "#",
                },
                {
                    "image_url": "https://via.placeholder.com/88x66/11A683/FFFFFF?text=A2",
                    "image_alt": "Article 2",
                    "title": "Что важно для Outlook-совместимости",
                    "text": "Памятка по табличной верстке и inline CSS.",
                    "url": "#",
                },
                {
                    "image_url": "https://via.placeholder.com/88x66/172033/FFFFFF?text=A3",
                    "image_alt": "Article 3",
                    "title": "Как готовить данные для персонализации",
                    "text": "Почему блоки должны иметь предсказуемые параметры.",
                    "url": "#",
                },
            ],
        },
    ),
    "video_preview": BlockMetadata(
        "video_preview",
        "Превью видео с кнопкой просмотра.",
        {
            "image_url": "Кадр видео.",
            "image_alt": "Alt-текст.",
            "title": "Заголовок.",
            "button_text": "Текст кнопки.",
            "button_url": "URL видео.",
        },
        {
            "image_url": "https://via.placeholder.com/600x300/246BFE/FFFFFF?text=Video",
            "image_alt": "Video preview",
            "title": "Посмотрите короткий обзор",
            "button_text": "Смотреть видео",
            "button_url": "#",
        },
    ),
    "cta": BlockMetadata(
        "cta",
        "Компактный призыв к действию.",
        {"title": "Заголовок.", "text": "Описание.", "button_text": "Текст кнопки.", "button_url": "URL кнопки."},
        {
            "title": "Готовы начать?",
            "text": "Запустите первую кампанию уже сегодня.",
            "button_text": "Начать",
            "button_url": "#",
        },
    ),
    "cta_banner": BlockMetadata(
        "cta_banner",
        "Акцентный баннер с CTA.",
        {"title": "Заголовок.", "text": "Описание.", "button_text": "Текст кнопки.", "button_url": "URL кнопки."},
        {
            "title": "Персональные рассылки быстрее",
            "text": "Используйте готовые блоки и единую дизайн-систему.",
            "button_text": "Попробовать",
            "button_url": "#",
        },
    ),
    "benefits": BlockMetadata(
        "benefits",
        "Три преимущества продукта или услуги.",
        {
            "title": "Заголовок секции.",
            "benefits": "Список из объектов title, text.",
        },
        {
            "title": "Преимущества",
            "benefits": [
                {"title": "Модульность", "text": "Блоки легко комбинировать."},
                {"title": "Скорость", "text": "Меньше ручной верстки."},
                {"title": "Готовность к ML", "text": "Структура подходит для последующей персонализации."},
            ],
        },
    ),
    "feature_list": BlockMetadata(
        "feature_list",
        "Список возможностей с отметками.",
        {"title": "Заголовок секции.", "items": "Список текстовых пунктов."},
        {
            "title": "Что можно сделать",
            "items": [
                "Собрать письмо из независимых блоков.",
                "Переиспользовать шаблоны в разных сценариях.",
                "Передавать структурированные данные в Jinja2.",
                "Подготовить основу для ML-персонализации.",
            ],
        },
    ),
    "icon_text": BlockMetadata(
        "icon_text",
        "Список тезисов с текстовыми иконками.",
        {"items": "Список объектов icon, title, text."},
        {
            "items": [
                {"icon": "01", "title": "Сегментация", "text": "Разные блоки для разных аудиторий."},
                {"icon": "02", "title": "Контроль", "text": "Единые параметры и шаблоны."},
            ]
        },
    ),
    "statistics": BlockMetadata(
        "statistics",
        "Три числовых показателя.",
        {"stats": "Список объектов value, label."},
        {
            "stats": [
                {"value": "32%", "label": "рост CTR"},
                {"value": "2x", "label": "быстрее запуск"},
                {"value": "24/7", "label": "доступность"},
            ]
        },
    ),
    "social_proof": BlockMetadata(
        "social_proof",
        "Социальное доказательство с ключевой метрикой.",
        {"title": "Заголовок.", "text": "Описание.", "metric": "Крупная метрика.", "metric_label": "Подпись метрики."},
        {
            "title": "Команды быстрее выпускают кампании",
            "text": "Модульная структура снижает зависимость от ручной верстки.",
            "metric": "2.4x",
            "metric_label": "ускорение запуска",
        },
    ),
    "testimonials": BlockMetadata(
        "testimonials",
        "Отзывы клиентов.",
        {"title": "Заголовок.", "items": "Список объектов quote, author, role."},
        {
            "title": "Отзывы",
            "items": [
                {"quote": "Команда стала выпускать рассылки заметно быстрее.", "author": "Анна Петрова", "role": "CMO"},
                {"quote": "Нам понравилась прозрачная структура блоков.", "author": "Игорь Смирнов", "role": "Product Lead"},
            ],
        },
    ),
    "case_study": BlockMetadata(
        "case_study",
        "Кейс с результатом.",
        {"label": "Метка.", "title": "Заголовок.", "text": "Описание.", "result": "Ключевой результат."},
        {
            "label": "Кейс",
            "title": "Как SaaS-команда ускорила выпуск кампаний",
            "text": "Команда перешла на модульные шаблоны и стала собирать письма из проверенных компонентов.",
            "result": "+28% к конверсии в демо",
        },
    ),
    "client_logos": BlockMetadata(
        "client_logos",
        "Сетка логотипов клиентов в текстовом виде.",
        {"title": "Заголовок.", "logos": "Список названий брендов."},
        {"title": "Нам доверяют", "logos": ["Northwind", "Contoso", "Fabrikam", "Globex"]},
    ),
    "team": BlockMetadata(
        "team",
        "Команда из нескольких сотрудников.",
        {"title": "Заголовок.", "members": "Список объектов name, role, image_url."},
        {
            "title": "Команда проекта",
            "members": [
                {"name": "Мария", "role": "Email strategist", "image_url": "https://via.placeholder.com/120x120/246BFE/FFFFFF?text=M"},
                {"name": "Алексей", "role": "Developer", "image_url": "https://via.placeholder.com/120x120/11A683/FFFFFF?text=A"},
                {"name": "Елена", "role": "Designer", "image_url": "https://via.placeholder.com/120x120/172033/FFFFFF?text=E"},
            ],
        },
    ),
    "employee": BlockMetadata(
        "employee",
        "Карточка одного сотрудника.",
        {"name": "Имя.", "role": "Должность.", "bio": "Описание.", "image_url": "Фото."},
        {
            "name": "Дмитрий Иванов",
            "role": "Руководитель продукта",
            "bio": "Помогает командам запускать email-кампании быстрее и аккуратнее.",
            "image_url": "https://via.placeholder.com/128x128/246BFE/FFFFFF?text=DI",
        },
    ),
    "product_card": BlockMetadata(
        "product_card",
        "Карточка товара.",
        {"title": "Название.", "price": "Цена.", "image_url": "Изображение.", "button_text": "Кнопка.", "button_url": "URL."},
        {
            "title": "Email-пакет Pro",
            "price": "4 900 ₽",
            "image_url": "https://via.placeholder.com/520x260/246BFE/FFFFFF?text=Product",
            "button_text": "Купить",
            "button_url": "#",
        },
    ),
    "product_grid": BlockMetadata(
        "product_grid",
        "Сетка товаров.",
        {"title": "Заголовок.", "products": "Список объектов title, price, image_url, button_url."},
        {
            "title": "Популярные товары",
            "products": [
                {"title": "Starter", "price": "990 ₽", "image_url": "https://via.placeholder.com/180x140/246BFE/FFFFFF?text=S", "button_url": "#"},
                {"title": "Pro", "price": "4 900 ₽", "image_url": "https://via.placeholder.com/180x140/11A683/FFFFFF?text=P", "button_url": "#"},
                {"title": "Team", "price": "9 900 ₽", "image_url": "https://via.placeholder.com/180x140/172033/FFFFFF?text=T", "button_url": "#"},
            ],
        },
    ),
    "pricing_table": BlockMetadata(
        "pricing_table",
        "Сравнение тарифов или пакетов.",
        {"title": "Заголовок секции.", "plans": "Список объектов name, price, description, button_text, button_url."},
        {
            "title": "Выберите пакет",
            "plans": [
                {"name": "Starter", "price": "990 ₽", "description": "Для первых кампаний.", "button_text": "Выбрать", "button_url": "#"},
                {"name": "Pro", "price": "4 900 ₽", "description": "Для регулярных рассылок.", "button_text": "Выбрать", "button_url": "#"},
                {"name": "Team", "price": "9 900 ₽", "description": "Для маркетинг-команд.", "button_text": "Выбрать", "button_url": "#"},
            ],
        },
    ),
    "service_card": BlockMetadata(
        "service_card",
        "Карточка услуги.",
        {"title": "Название.", "text": "Описание.", "items": "Список пунктов.", "button_text": "Кнопка.", "button_url": "URL."},
        {
            "title": "Внедрение email-конструктора",
            "text": "Поможем собрать библиотеку блоков под ваши кампании.",
            "items": ["Аудит шаблонов", "Дизайн-система", "Интеграция"],
            "button_text": "Обсудить проект",
            "button_url": "#",
        },
    ),
    "faq": BlockMetadata(
        "faq",
        "Список частых вопросов.",
        {"title": "Заголовок.", "items": "Список объектов question, answer."},
        {
            "title": "Вопросы",
            "items": [
                {"question": "Можно ли добавлять свои блоки?", "answer": "Да, достаточно создать шаблон и зарегистрировать данные."},
                {"question": "Готово ли это для ML?", "answer": "Структура блоков уже подходит для дальнейшего выбора алгоритмами."},
            ],
        },
    ),
    "timeline": BlockMetadata(
        "timeline",
        "Пошаговый план или таймлайн.",
        {"title": "Заголовок.", "steps": "Список объектов label, title, text."},
        {
            "title": "План запуска",
            "steps": [
                {"label": "1", "title": "Выбор блоков", "text": "Определяем структуру письма."},
                {"label": "2", "title": "Заполнение данных", "text": "Передаем параметры в Jinja2."},
                {"label": "3", "title": "Отправка", "text": "HTML готов для ESP-системы."},
            ],
        },
    ),
    "promo": BlockMetadata(
        "promo",
        "Промо-блок со скидкой или предложением.",
        {"discount": "Размер скидки.", "title": "Заголовок.", "text": "Описание.", "code": "Промокод.", "button_text": "Кнопка.", "button_url": "URL."},
        {
            "discount": "-30%",
            "title": "Специальное предложение",
            "text": "Скидка действует до конца недели.",
            "code": "EMAIL30",
            "button_text": "Получить скидку",
            "button_url": "#",
        },
    ),
    "coupon": BlockMetadata(
        "coupon",
        "Купон с промокодом и ссылкой.",
        {"label": "Метка.", "title": "Заголовок.", "text": "Описание.", "code": "Промокод.", "button_text": "Текст ссылки.", "button_url": "URL ссылки."},
        {
            "label": "Персональный бонус",
            "title": "Сохраните промокод",
            "text": "Используйте его при оформлении заказа.",
            "code": "MAIL20",
            "button_text": "Применить",
            "button_url": "#",
        },
    ),
    "divider": BlockMetadata(
        "divider",
        "Тонкий визуальный разделитель между секциями.",
        {},
        {},
    ),
    "spacer": BlockMetadata(
        "spacer",
        "Вертикальный отступ с настраиваемой высотой.",
        {"height": "Высота отступа в пикселях."},
        {"height": 16},
    ),
    "footer": BlockMetadata(
        "footer",
        "Подвал письма с контактами и отпиской.",
        {
            "company_name": "Название компании.",
            "address": "Адрес.",
            "unsubscribe_url": "Ссылка отписки.",
            "unsubscribe_text": "Текст ссылки.",
            "social_links": "Список объектов title, url.",
        },
        {
            "company_name": "Sample Mail",
            "address": "Екатеринбург, Россия",
            "unsubscribe_url": "#",
            "unsubscribe_text": "Отписаться",
            "social_links": [{"title": "Telegram", "url": "#"}, {"title": "Website", "url": "#"}],
        },
    ),
}


def get_block_metadata(name: str) -> BlockMetadata:
    try:
        return BLOCK_REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(sorted(BLOCK_REGISTRY))
        raise ValueError(f"Unknown block '{name}'. Available blocks: {available}") from exc


def get_block_example(name: str) -> Context:
    return deepcopy(get_block_metadata(name).example)
