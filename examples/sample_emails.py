from __future__ import annotations

from email_builder import EmailBuilder


def build_b2b_saas_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "FlowMail", "tagline": "B2B SaaS"})
    builder.add_block(
        "hero_split",
        {
            "eyebrow": "Для отделов маркетинга",
            "title": "Собирайте B2B-рассылки быстрее",
            "subtitle": "Модульный конструктор помогает запускать кампании без ручной верстки каждого письма.",
            "button_text": "Запросить демо",
            "button_url": "#demo",
            "image_url": "https://via.placeholder.com/260x220/246BFE/FFFFFF?text=B2B",
            "image_alt": "B2B dashboard",
        },
    )
    builder.add_block("benefits")
    builder.add_block("social_proof")
    builder.add_block("statistics")
    builder.add_block("case_study")
    builder.add_block("cta")
    builder.add_block("footer", {"company_name": "FlowMail"})
    return builder.render({"preheader": "B2B SaaS письмо из модульных блоков"})


def build_ecommerce_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "MarketPlus", "tagline": "Интернет-магазин"})
    builder.add_block(
        "promo",
        {
            "discount": "-25%",
            "title": "Подборка недели",
            "text": "Собрали товары, которые чаще всего добавляют в избранное.",
            "code": "WEEK25",
        },
    )
    builder.add_block("coupon", {"label": "Для подписчиков", "code": "WEEK25", "title": "Промокод уже активен"})
    builder.add_block("product_grid")
    builder.add_block("testimonials")
    builder.add_block("footer", {"company_name": "MarketPlus"})
    return builder.render({"preheader": "Скидка 25% на подборку недели"})


def build_corporate_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "Acme Corp", "tagline": "Новости компании"})
    builder.add_block(
        "text",
        {
            "title": "Итоги квартала",
            "paragraphs": [
                "Мы завершили квартал с ростом ключевых метрик и расширили продуктовую команду.",
                "Ниже собраны главные обновления и ближайшие планы.",
            ],
        },
    )
    builder.add_block("article_list", {"title": "Главные новости"})
    builder.add_block("divider")
    builder.add_block("timeline")
    builder.add_block("team")
    builder.add_block("footer", {"company_name": "Acme Corp"})
    return builder.render({"preheader": "Корпоративные новости и планы"})


def build_promo_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "Sample Mail", "tagline": "Акция"})
    builder.add_block("hero_compact", {"title": "Большая акция на email-пакеты", "button_text": "Забрать предложение"})
    builder.add_block("promo")
    builder.add_block("pricing_table")
    builder.add_block("coupon", {"label": "Код акции", "code": "SALE30"})
    builder.add_block("cta_banner")
    builder.add_block("faq")
    builder.add_block("footer")
    return builder.render({"preheader": "Акционное предложение Sample Mail"})


def build_welcome_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "Sample Mail", "tagline": "Добро пожаловать"})
    builder.add_block(
        "hero",
        {
            "eyebrow": "Добро пожаловать",
            "title": "Вы в системе",
            "subtitle": "Начните с готового письма или соберите свое из независимых блоков.",
            "button_text": "Открыть кабинет",
        },
    )
    builder.add_block("feature_list", {"title": "Начните с этих возможностей"})
    builder.add_block("icon_text")
    builder.add_block("video_preview")
    builder.add_block("cta")
    builder.add_block("footer")
    return builder.render({"preheader": "Первый шаг в Sample Mail"})


def build_product_launch_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "LaunchDesk", "tagline": "Запуск продукта"})
    builder.add_block(
        "hero_split",
        {
            "eyebrow": "Новый релиз",
            "title": "Представляем обновленный конструктор кампаний",
            "subtitle": "Новые блоки, быстрый предпросмотр и единая структура данных для команды маркетинга.",
            "button_text": "Посмотреть релиз",
            "button_url": "#release",
            "image_url": "https://via.placeholder.com/260x220/11A683/FFFFFF?text=Release",
            "image_alt": "Release preview",
        },
    )
    builder.add_block("image_right")
    builder.add_block("feature_list", {"title": "Ключевые изменения"})
    builder.add_block("benefits", {"title": "Что появилось в релизе"})
    builder.add_block("video_preview", {"title": "Короткий обзор возможностей"})
    builder.add_block("footer", {"company_name": "LaunchDesk"})
    return builder.render({"preheader": "Новый релиз LaunchDesk уже доступен"})


def build_event_invitation_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "MailConf", "tagline": "Онлайн-встреча"})
    builder.add_block(
        "hero",
        {
            "eyebrow": "Вебинар",
            "title": "Как строить email-рассылки из модульных блоков",
            "subtitle": "Разберем архитектуру шаблонов, адаптивную верстку и подготовку данных для будущей ML-персонализации.",
            "button_text": "Зарегистрироваться",
            "button_url": "#register",
        },
    )
    builder.add_block("timeline", {"title": "Программа вебинара"})
    builder.add_block("employee", {"name": "Ольга Кузнецова", "role": "Email architect"})
    builder.add_block("social_proof", {"title": "Практический формат", "metric": "45 мин", "metric_label": "разбора и вопросов"})
    builder.add_block("cta_banner", {"title": "Забронируйте место", "button_text": "Участвовать"})
    builder.add_block("footer", {"company_name": "MailConf"})
    return builder.render({"preheader": "Приглашение на вебинар по email-архитектуре"})


def build_newsletter_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "DigestLab", "tagline": "Еженедельный дайджест"})
    builder.add_block(
        "text",
        {
            "title": "Главные обновления недели",
            "paragraphs": [
                "Мы собрали полезные материалы о шаблонах, доставляемости и автоматизации рассылок.",
                "В выпуске есть практические идеи для команд, которые хотят быстрее тестировать email-гипотезы.",
            ],
        },
    )
    builder.add_block("article_list")
    builder.add_block("divider")
    builder.add_block("gallery")
    builder.add_block("client_logos", {"title": "Источники и партнеры выпуска"})
    builder.add_block("faq", {"title": "Коротко о выпуске"})
    builder.add_block("footer", {"company_name": "DigestLab"})
    return builder.render({"preheader": "Еженедельный дайджест DigestLab"})


def build_cart_abandonment_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "MarketPlus", "tagline": "Вы оставили товары"})
    builder.add_block(
        "text",
        {
            "title": "Ваши товары все еще ждут",
            "paragraphs": [
                "Мы сохранили корзину, чтобы вы могли вернуться к покупке в удобный момент.",
                "Добавили небольшой бонус на завершение заказа.",
            ],
        },
    )
    builder.add_block("product_card", {"title": "Набор для email-маркетинга", "price": "3 490 ₽"})
    builder.add_block("promo", {"discount": "-10%", "code": "BACK10", "title": "Бонус на завершение заказа"})
    builder.add_block("coupon", {"label": "Вернитесь к заказу", "code": "BACK10", "button_text": "Применить бонус"})
    builder.add_block("cta", {"title": "Вернуться в корзину", "button_text": "Открыть корзину"})
    builder.add_block("footer", {"company_name": "MarketPlus"})
    return builder.render({"preheader": "Корзина сохранена, бонус внутри"})


def build_reactivation_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "Sample Mail", "tagline": "Мы скучали"})
    builder.add_block(
        "hero",
        {
            "eyebrow": "Возвращайтесь",
            "title": "У вас появились новые возможности",
            "subtitle": "Мы обновили библиотеку блоков, добавили новые примеры писем и улучшили структуру данных.",
            "button_text": "Посмотреть обновления",
            "button_url": "#updates",
        },
    )
    builder.add_block("text_quote", {"author": "Команда Sample Mail", "role": "Product team"})
    builder.add_block("statistics")
    builder.add_block("service_card")
    builder.add_block("cta_banner", {"title": "Продолжим с того места, где остановились?"})
    builder.add_block("footer")
    return builder.render({"preheader": "Новые возможности ждут вас в Sample Mail"})


def build_onboarding_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "Sample Mail", "tagline": "Онбординг"})
    builder.add_block(
        "hero",
        {
            "eyebrow": "Шаг 1",
            "title": "Соберите первое письмо за несколько минут",
            "subtitle": "Начните с базовой структуры: шапка, главный экран, преимущества, CTA и подвал.",
            "button_text": "Создать письмо",
            "button_url": "#create",
        },
    )
    builder.add_block("timeline", {"title": "Первые шаги"})
    builder.add_block("feature_list", {"title": "Проверочный список запуска"})
    builder.add_block("icon_text")
    builder.add_block("video_preview", {"title": "Посмотрите, как работает сборка письма"})
    builder.add_block("footer")
    return builder.render({"preheader": "Онбординг Sample Mail: первый шаг"})


def build_case_study_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "FlowMail", "tagline": "История клиента"})
    builder.add_block(
        "hero",
        {
            "eyebrow": "Customer story",
            "title": "Как команда продаж ускорила email-коммуникации",
            "subtitle": "Кейс о том, как модульные письма помогают быстрее запускать персональные цепочки.",
            "button_text": "Читать кейс",
            "button_url": "#case",
        },
    )
    builder.add_block("case_study")
    builder.add_block("text_quote")
    builder.add_block("testimonials")
    builder.add_block("social_proof", {"title": "Результат после внедрения", "metric": "+28%", "metric_label": "конверсия в демо"})
    builder.add_block("cta", {"title": "Хотите такой же процесс?", "button_text": "Обсудить внедрение"})
    builder.add_block("footer", {"company_name": "FlowMail"})
    return builder.render({"preheader": "Кейс FlowMail о модульных email-письмах"})


def build_service_offer_email() -> str:
    builder = EmailBuilder()
    builder.add_block("header", {"logo_text": "Email Studio", "tagline": "Услуги"})
    builder.add_block(
        "hero",
        {
            "eyebrow": "Для бизнеса",
            "title": "Внедрим библиотеку email-блоков под ваш бренд",
            "subtitle": "Подготовим шаблоны, параметры и документацию, чтобы команда быстрее выпускала рассылки.",
            "button_text": "Получить оценку",
            "button_url": "#estimate",
        },
    )
    builder.add_block("service_card")
    builder.add_block("benefits", {"title": "Что входит в работу"})
    builder.add_block("pricing_table", {"title": "Форматы сотрудничества"})
    builder.add_block("client_logos")
    builder.add_block("footer", {"company_name": "Email Studio"})
    return builder.render({"preheader": "Коммерческое предложение Email Studio"})
