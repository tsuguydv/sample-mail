// App state & utilities (localStorage-backed)
window.Store = (() => {
  const KEYS = {
    token: "taskflock_token",
    company: "taskflock_company",
    emailParams: "taskflock_emailParams",
    selectedTemplate: "taskflock_selectedTemplate",
    generation: "taskflock_generation",
    sessionId: "taskflock_sessionId",
    generatedEmailId: "taskflock_generatedEmailId",
    imageIndex: "taskflock_imageIndex",
    textIndex: "taskflock_textIndex",
    ctaIndex: "taskflock_ctaIndex",
    theme: "taskflock_theme",
    customBlockLayout: "taskflock_customBlockLayout",
  };

  function getJSON(key, fallback){
    try{
      const v = localStorage.getItem(key);
      return v ? JSON.parse(v) : fallback;
    }catch{ return fallback; }
  }
  function setJSON(key, value){
    localStorage.setItem(key, JSON.stringify(value));
  }

  function getToken(){ return localStorage.getItem(KEYS.token); }
  function setToken(t){
    if(!t) localStorage.removeItem(KEYS.token);
    else localStorage.setItem(KEYS.token, t);
  }

  function getCompany(){ return getJSON(KEYS.company, null); }
  function setCompany(v){ setJSON(KEYS.company, v); }

  function getEmailParams(){ return getJSON(KEYS.emailParams, null); }
  function setEmailParams(v){ setJSON(KEYS.emailParams, v); }

  function getSelectedTemplate(){ return getJSON(KEYS.selectedTemplate, null); }
  function setSelectedTemplate(v){ setJSON(KEYS.selectedTemplate, v); }

  function getGeneration(){ return getJSON(KEYS.generation, null); }
  function setGeneration(v){ setJSON(KEYS.generation, v); }

  function getSessionId(){ return localStorage.getItem(KEYS.sessionId); }
  function setSessionId(v){
    if(v==null) localStorage.removeItem(KEYS.sessionId);
    else localStorage.setItem(KEYS.sessionId, String(v));
  }
  function getGeneratedEmailId(){
    const raw = localStorage.getItem(KEYS.generatedEmailId);
    if(raw == null || raw === "") return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }
  function setGeneratedEmailId(v){
    if(v==null || v==="") localStorage.removeItem(KEYS.generatedEmailId);
    else localStorage.setItem(KEYS.generatedEmailId, String(v));
  }

  function getIndex(key){ return Number(localStorage.getItem(key) ?? "0") || 0; }
  function setIndex(key, v){ localStorage.setItem(key, String(v ?? 0)); }

  function getTheme(){
    const v = localStorage.getItem(KEYS.theme);
    return v === "dark" ? "dark" : "light";
  }
  function setTheme(v){
    const val = v === "dark" ? "dark" : "light";
    localStorage.setItem(KEYS.theme, val);
    document.documentElement.setAttribute("data-theme", val);
  }

  function getLanguage(){
    const v = (localStorage.getItem(KEYS.language) || "").toLowerCase();
    return v === "en" ? "en" : "ru";
  }
  function setLanguage(v){
    const val = (v || "").toLowerCase() === "en" ? "en" : "ru";
    localStorage.setItem(KEYS.language, val);
    document.documentElement.lang = val;
  }

  function getCustomBlockLayout(){ return getJSON(KEYS.customBlockLayout, null); }
  function setCustomBlockLayout(v){
    if(v == null) localStorage.removeItem(KEYS.customBlockLayout);
    else setJSON(KEYS.customBlockLayout, v);
  }

  return {
    KEYS,
    getToken, setToken,
    getCompany, setCompany,
    getEmailParams, setEmailParams,
    getSelectedTemplate, setSelectedTemplate,
    getGeneration, setGeneration,
    getSessionId, setSessionId,
    getGeneratedEmailId, setGeneratedEmailId,
    getImageIndex: () => getIndex(KEYS.imageIndex),
    getTextIndex: () => getIndex(KEYS.textIndex),
    getCtaIndex: () => getIndex(KEYS.ctaIndex),
    setImageIndex: (v) => setIndex(KEYS.imageIndex, v),
    setTextIndex: (v) => setIndex(KEYS.textIndex, v),
    setCtaIndex: (v) => setIndex(KEYS.ctaIndex, v),
    getTheme,
    setTheme,
    getLanguage,
    setLanguage,
    getCustomBlockLayout,
    setCustomBlockLayout,
  };
})();

function $(sel, root=document){ return root.querySelector(sel); }
function $all(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }

function requireAuth(){
  const t = Store.getToken();
  if(!t){
    window.location.href = "login.html";
    return false;
  }
  return true;
}

async function logout(){
  try{
    if(typeof API !== "undefined" && API.logoutCurrentSession){
      await API.logoutCurrentSession();
    }
  }catch{
    // best effort; still clear local auth
  }
  Store.setToken(null);
  window.location.href = "login.html";
}

function downloadBlob(blob, filename){
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// Simple i18n dictionaries (RU / EN) for key UI texts
window.I18N = {
  ru: {
    "nav.company": "Информация о компании",
    "nav.generate": "Создать новое письмо",
    "nav.generated": "Письма и статусы",
    "nav.generations": "Статусы генерации",
    "nav.account": "Настройки аккаунта",
    "nav.templates": "Шаблоны",
    "nav.logoPlaceholder": "Логотип",
    "nav.help": "Нужна помощь?",
    "nav.logout": "Выйти",
    "nav.tokens": "{n} токенов",
    "nav.reputation": "Репутация",
    "nav.reputation.hint.orange": "Ниже 40: без генерации изображений. Возвраты недоступны.",
    "nav.reputation.hint.blocked": "0: генерация заблокирована до нового биллинг-периода.",
    "plan.freeHint": "Бесплатно: осталось {left} из {limit} генераций сегодня · {balance} токенов",
    "plan.tokenHint": "{balance} токенов · текст {text} · изображение {image} (до {per} за письмо с картинкой)",
    "account.tokens.title": "Токены",
    "account.tokens.upgrade": "Улучшить план",
    "account.tokens.buy": "Купить токены",
    "account.plan.subscribed": "подписка активна",
    "account.plan.notSubscribed": "без подписки",
    "page.title.plans": "smart-letters — Планы",
    "plans.title": "Улучшить план",
    "plans.subtitle": "Бесплатный план или подписка Pro — выберите то, что подходит.",
    "plans.free.generationsPerDay": "{n} генераций в день без токенов",
    "plans.free.noTokens": "Без ежемесячных токенов и пополнений",
    "plans.free.default": "По умолчанию",
    "plans.status.onFree": "Сейчас активен бесплатный план",
    "plans.empty": "Планы не настроены",
    "plans.includedTokens": "{n} токенов в месяц",
    "plans.pricingBreakdown": "Генерация: {text} за текст · {image} за изображение",
    "plans.extraTokenRate": "Доп. токены: {price} за токен",
    "plans.button.subscribe": "Подписаться",
    "plans.button.active": "Текущий план",
    "plans.status.choose": "Выберите план и оплатите через PayPal",
    "plans.status.subscribed": "Активный план: {plan}",
    "page.title.buyTokens": "smart-letters — Покупка токенов",
    "buyTokens.title": "Купить токены",
    "buyTokens.subtitle": "Пополните баланс по тарифу вашего плана после оформления подписки.",
    "buyTokens.label.amount": "Количество токенов",
    "buyTokens.pricePreview": "{tokens} токенов · {price}",
    "buyTokens.rateLine": "Тариф: {price} за токен · баланс: {bal}",
    "buyTokens.needSubscription": "Сначала оформите подписку на странице планов.",
    "buyTokens.ready": "Введите количество и оплатите через PayPal.",
    "buyTokens.button.buy": "Оплатить через PayPal",
    "buyTokens.link.plans": "Нужна подписка? Улучшить план",
    "buyTokens.success": "Токены зачислены на баланс.",
    "buyTokens.captureFailed": "Оплата прошла, но зачисление не удалось — обратитесь в поддержку.",
    "templates.cost.paid": "Стоимость: {total} токенов (текст {text} + изображение {image}) · баланс {bal}",
    "templates.cost.insufficient": "Нужно {total} токенов (текст {text} + изображение {image}) · баланс {bal}",
    "templates.cost.freeSlot": "Будет использована бесплатная генерация на сегодня",
    "templates.cost.toggleTotal": "{n} токенов",
    "templates.cost.toggleFree": "0 токенов (бесплатно)",
    "templates.cost.tokens": "{n} ток.",
    "templates.cost.label": "К оплате",
    "templates.cost.selectTemplate": "Выберите шаблон",
    "templates.cost.lineText": "Текст письма",
    "templates.cost.lineImage": "Изображение",
    "templates.cost.lineTotal": "Итого",
    "templates.cost.lineFree": "Бесплатно",
    "templates.cost.noImages": "Изображение недоступно (репутация {rep})",
    "templates.cost.blocked": "Генерация недоступна (репутация 0)",
    "landing.title": "smart-letters",
    "landing.description": "Сервис для генерации email-писем с помощью ИИ. Создайте письмо за минуты, выберите лучший вариант и скачайте результат.",
    "landing.button.login": "Войти",
    "company.title": "Данные о компании",
    "company.subtitle": "Заполните данные, на основе которых будут генерироваться письма.",
    "company.hint": "<strong>Обязательные поля:</strong> название компании, ниша и важная информация о компании, описание продуктов или услуг компании.<br /><strong>Необязательные поля:</strong> логотип, сайт компании, почта, социальные сети компании.",
    "company.label.name": "Название компании *",
    "company.label.niche": "Ниша компании и другая важная информация о компании *",
    "company.label.description": "Описание продуктов или услуг компании *",
    "company.label.logo": "Логотип (необязательно)",
    "company.label.email": "Почта компании (необязательно)",
    "company.label.phone": "Телефон (необязательно)",
    "company.label.website": "Сайт компании (необязательно)",
    "company.label.socials": "Социальные сети компании (необязательно)",
    "company.label.comments": "Комментарии или пожелания",
    "company.placeholder.socials": "Ссылки через запятую",
    "company.button.next": "Далее",
    "company.button.saving": "Сохранение…",
    "company.error.selectImage": "Выберите изображение",
    "company.error.name": "Введите название компании",
    "company.error.niche": "Введите нишу",
    "company.error.description": "Введите описание продукта или услуги",
    "company.error.save": "Ошибка сохранения",
    "params.title": "Параметры письма",
    "params.subtitle": "Задайте тему письма и важные параметры.",
    "params.hint": "<strong>Параметры письма:</strong> о чём писать в письме, пожелания к картинке, ссылка для кнопки в письме.",
    "params.label.subject": "О чём писать письмо *",
    "params.label.imageWishes": "Пожелания к картинке",
    "params.label.ctaLink": "Ссылка для кнопки в письме",
    "params.placeholder.imageWishes": "Стиль, тема, цвета",
    "params.placeholder.cta": "https://…",
    "params.label.colorScheme": "Цветовая схема письма",
    "params.option.notSelected": "Не выбрано",
    "params.option.light": "Светлая",
    "params.option.dark": "Тёмная",
    "params.option.brand": "Брендовая",
    "params.button.next": "Далее",
    "params.button.back": "Назад",
    "params.error.subject": "Укажите, о чём писать письмо",
    "landing.title": "smart-letters",
    "landing.description": "Сервис для генерации email-писем с помощью ИИ. Создайте письмо за минуты, выберите лучший вариант и скачайте результат.",
    "landing.button.login": "Войти",
    "login.title": "Вход в систему",
    "login.button": "Войти",
    "login.label.email": "Email",
    "login.label.password": "Пароль",
    "login.footer.noaccount": "Нет аккаунта?",
    "login.footer.create": "Создать",
    "login.footer.home": "На главную",
    "login.error": "Ошибка входа",
    "login.resendVerification": "Отправить письмо повторно",
    "login.resendVerification.sent": "Письмо для подтверждения отправлено.",
    "register.title": "Создание аккаунта",
    "register.button": "Зарегистрироваться",
    "register.label.email": "Email",
    "register.label.password": "Пароль",
    "register.legalConsent": "Я соглашаюсь с <a href=\"terms.html\" target=\"_blank\" rel=\"noopener\">Условиями использования</a> и <a href=\"privacy.html\" target=\"_blank\" rel=\"noopener\">Политикой конфиденциальности</a>.",
    "register.footer.hasaccount": "Уже есть аккаунт?",
    "register.footer.login": "Войти",
    "templates.title": "Выбор шаблона",
    "templates.subtitle": "Выберите один шаблон для генерации писем, затем нажмите «Сгенерировать».",
    "templates.button.generate": "Сгенерировать письма",
    "templates.button.generating": "Генерация…",
    "templates.button.back": "Назад",
    "templates.error.load": "Не удалось загрузить шаблоны",
    "templates.error.generate": "Ошибка генерации",
    "templates.empty": "Шаблоны не найдены.",
    "templates.loading": "Загрузка шаблонов…",
    "templates.preview.head": "Превью шаблона",
    "templates.preview.showStructure": "Показать структуру",
    "templates.preview.hideStructure": "Скрыть структуру",
    "template.t1": "Классический",
    "template.t2": "Минималистичный",
    "template.t3": "Яркий призыв",
    "template.t4": "Современная карточка",
    "template.m1": "Welcome (модули)",
    "template.m2": "B2B SaaS",
    "template.m3": "Акция",
    "template.m4": "Корпоративное",
    "template.m5": "Магазин",
    "template.custom": "Свой макет",
    "templates.modularBadge": "Модули",
    "templates.button.builder": "Конструктор блоков",
    "builder.title": "Конструктор письма",
    "builder.subtitle": "Соберите письмо из блоков и используйте его для генерации.",
    "builder.palette": "Блоки",
    "builder.layout": "Структура письма",
    "builder.preview": "Предпросмотр",
    "builder.addBlock": "Добавить",
    "builder.emptyLayout": "Добавьте блоки из палитры слева.",
    "builder.useLayout": "Использовать для генерации",
    "builder.backTemplates": "К шаблонам",
    "builder.moveUp": "Вверх",
    "builder.moveDown": "Вниз",
    "builder.remove": "Удалить",
    "builder.loadPreset": "Загрузить пресет",
    "builder.previewSubject": "Тема вашего письма",
    "builder.previewBody": "<p>Текст письма от ИИ появится здесь после генерации.</p>",
    "builder.previewCta": "Перейти",
    "page.title.builder": "smart-letters — Конструктор",
    "editor.block.header": "Шапка",
    "editor.block.hero": "Главный экран",
    "editor.block.heroSplit": "Экран: текст + фото",
    "editor.block.heroCompact": "Компактный баннер",
    "editor.block.text": "Текст",
    "editor.block.quote": "Цитата",
    "editor.block.cta": "Кнопка",
    "editor.block.ctaBanner": "Баннер с кнопкой",
    "editor.block.footer": "Подвал",
    "editor.block.imageFull": "Изображение на всю ширину",
    "editor.block.imageLeft": "Фото слева",
    "editor.block.imageRight": "Фото справа",
    "editor.block.benefits": "Преимущества",
    "editor.block.promo": "Акция",
    "editor.block.products": "Товары",
    "editor.block.divider": "Разделитель",
    "editor.block.spacer": "Отступ",
    "editor.block.gallery": "Галерея",
    "editor.block.articleList": "Список статей",
    "editor.block.videoPreview": "Видео",
    "editor.block.featureList": "Список возможностей",
    "editor.block.iconText": "Иконки с текстом",
    "editor.block.statistics": "Статистика",
    "editor.block.socialProof": "Социальное доказательство",
    "editor.block.testimonials": "Отзывы",
    "editor.block.caseStudy": "Кейс",
    "editor.block.clientLogos": "Логотипы клиентов",
    "editor.block.team": "Команда",
    "editor.block.employee": "Сотрудник",
    "editor.block.productCard": "Карточка товара",
    "editor.block.pricingTable": "Тарифы",
    "editor.block.serviceCard": "Услуга",
    "editor.block.faq": "FAQ",
    "editor.block.timeline": "Таймлайн",
    "editor.block.coupon": "Купон",
    "editor.noFields": "Нет редактируемых полей.",
    "editor.aiImage": "Вариант изображения ИИ",
    "editor.imageVariant": "Изображение",
    "editor.variant": "Вариант",
    "editor.ctaLabel": "Текст кнопки",
    "editor.ctaLink": "Ссылка",
    "editor.align": "Выравнивание",
    "editor.default": "По умолчанию",
    "page.title.myTemplates": "smart-letters — Мои шаблоны",
    "myTemplates.title": "Шаблоны писем",
    "myTemplates.subtitle": "Создавайте, редактируйте и используйте макеты для генерации.",
    "myTemplates.builtin": "Встроенные",
    "myTemplates.saved": "Мои шаблоны",
    "myTemplates.create": "Создать шаблон",
    "myTemplates.edit": "Редактировать",
    "myTemplates.use": "Использовать",
    "myTemplates.delete": "Удалить",
    "myTemplates.empty": "Пока нет сохранённых шаблонов.",
    "myTemplates.deleteConfirm": "Удалить этот шаблон?",
    "myTemplates.blocks": "{n} блоков",
    "myTemplates.save": "Сохранить шаблон",
    "myTemplates.namePlaceholder": "Название шаблона",
    "myTemplates.nameRequired": "Введите название шаблона",
    "myTemplates.chooseForGeneration": "Выбрать для генерации",
    "common.error.saveFailed": "Не удалось сохранить",
    "common.error.previewFailed": "Не удалось обновить предпросмотр",
    "common.error.loadFailed": "Не удалось загрузить данные",
    "common.error.templateLimit": "Достигнут лимит сохранённых шаблонов",
    "compose.title": "Соберите письмо",
    "compose.subtitle": "Свайпайте по каждому блоку влево/вправо или нажимайте стрелки, чтобы выбрать вариант.",
    "compose.text.clickToEdit": "Нажмите на текст письма в блоке ниже, чтобы изменить его прямо здесь (сохраняется при уходе с поля и при переходе к результату).",
    "compose.section.image": "Картинка",
    "compose.section.text": "Текст письма",
    "compose.section.cta": "Кнопка (CTA)",
    "compose.aria.image": "Выбор изображения",
    "compose.aria.text": "Выбор текста",
    "compose.aria.cta": "Выбор кнопки",
    "compose.empty.text": "Нет данных письма. Начните с выбора шаблона.",
    "compose.empty.link": "К выбору шаблона",
    "compose.button.edit": "Запросить правки",
    "compose.button.result": "Перейти к результату",
    "result.title": "Итоговое письмо",
    "result.subtitle": "Редактируйте слева, справа — полный предпросмотр.",
    "result.subtitleNew": "Редактируются только секции, которые есть в письме. Превью обновляется сразу.",
    "result.editor.hint": "Каждая секция ниже соответствует блоку в письме. Раскройте секцию, чтобы изменить текст или стиль.",
    "result.editor.loading": "Загрузка секций письма…",
    "result.subtitleLong": "Скачайте письмо для использования в любом сервисе рассылок.",
    "result.button.download": "Скачать письмо",
    "result.button.downloading": "Скачивание…",
    "result.button.save": "Сохранить в текущее письмо",
    "result.button.saveCopy": "Сохранить как копию",
    "result.button.saving": "Сохранение…",
    "result.button.back": "К списку писем",
    "result.empty.text": "Нет данных письма.",
    "result.empty.link": "К выбору шаблона",
    "result.error.noSession": "Нет сессии для экспорта. Вернитесь к шаблонам.",
    "result.error.download": "Ошибка скачивания",
    "result.error.noEmailSelected": "Это новое письмо. Откройте сохранённое письмо или используйте «Сохранить как копию».",
    "result.error.save": "Не удалось сохранить письмо",
    "result.copy.prompt": "Введите название копии",
    "result.copy.defaultName": "Копия письма",
    "result.copy.saved": "Копия сохранена",
    "result.image.alt": "Изображение",
    "result.logo.alt": "Логотип",
    "result.label.imageVariant": "Вариант изображения",
    "result.label.textVariant": "Вариант текста",
    "result.label.ctaVariant": "Вариант кнопки",
    "result.label.textHtml": "Текст письма (HTML)",
    "result.label.ctaLabel": "Текст кнопки",
    "result.label.ctaHref": "Ссылка кнопки",
    "modal.edit.title": "Запросить правки",
    "modal.edit.subtitle": "Заполните только те поля, которые нужно изменить. Пустое поле — модуль не меняется.",
    "modal.edit.label.image": "Правки к картинке",
    "modal.edit.label.text": "Правки к тексту письма",
    "modal.edit.label.cta": "Правки к кнопке",
    "modal.edit.submit": "Отправить",
    "modal.edit.cancel": "Отмена",
    "theme.toggle": "Переключить тему",
    "theme.day": "День",
    "theme.night": "Ночь",
    "page.title.login": "smart-letters — Вход",
    "page.title.register": "smart-letters — Регистрация",
    "page.title.company": "smart-letters — Компания",
    "page.title.params": "smart-letters — Параметры",
    "page.title.templates": "smart-letters — Шаблоны",
    "page.title.compose": "smart-letters — Композиция",
    "page.title.result": "smart-letters — Результат",
    "page.title.landing": "smart-letters",
    "page.title.generatedEmails": "smart-letters — Письма и статусы",
    "page.title.account": "smart-letters — Настройки аккаунта",
    "page.title.generations": "smart-letters — Статусы генерации",
    "nav.langSwitch": "Сменить язык",
    "common.error": "Ошибка",
    "register.error": "Ошибка регистрации",
    "register.success.verify": "Регистрация успешна. Проверьте почту и подтвердите аккаунт перед входом.",
    "generatedEmails.title": "Письма и статусы генерации",
    "generatedEmails.subtitle": "Активные задачи генерации и история сохранённых писем.",
    "generatedEmails.empty": "Пока нет сохранённых писем.",
    "generatedEmails.placeholder.title": "Название",
    "generatedEmails.placeholder.tags": "Теги (через запятую)",
    "generatedEmails.favorite.on": "★ В избранном",
    "generatedEmails.favorite.off": "☆ В избранное",
    "generatedEmails.button.open": "Открыть",
    "generatedEmails.button.delete": "Удалить",
    "generatedEmails.confirm.delete": "Удалить это письмо?",
    "generatedEmails.error.load": "Не удалось загрузить список писем",
    "generatedEmails.error.invalidId": "Некорректный id письма в списке",
    "generatedEmails.error.update": "Не удалось обновить",
    "generatedEmails.error.saveDetails": "Не удалось сохранить данные",
    "generatedEmails.error.open": "Не удалось открыть",
    "generatedEmails.error.delete": "Не удалось удалить",
    "generatedEmails.metaSubject": "Тема",
    "generatedEmails.metaTemplate": "Шаблон",
    "generatedEmails.col.type": "Тип",
    "generatedEmails.ctaNew": "Создать письмо",
    "generatedEmails.filter.subject": "Тема",
    "generatedEmails.filter.subjectPlaceholder": "Поиск по теме...",
    "generatedEmails.filter.template": "Шаблон",
    "generatedEmails.filter.status": "Статус",
    "generatedEmails.filter.from": "С",
    "generatedEmails.filter.to": "По",
    "generatedEmails.filter.errorOnly": "Только ошибки",
    "generatedEmails.filter.all": "Все",
    "generatedEmails.filter.no": "Нет",
    "generatedEmails.filter.yes": "Да",
    "generatedEmails.emptyRows": "Записи не найдены.",
    "generatedEmails.type.job": "Задача",
    "generatedEmails.type.email": "Письмо",
    "generatedEmails.menu.actions": "Действия",
    "generatedEmails.job.retry": "Повторить",
    "generatedEmails.job.remove": "Убрать",
    "generatedEmails.job.confirmRemove": "Убрать эту неудачную генерацию из списка?",
    "generatedEmails.job.retryError": "Не удалось перезапустить задачу",
    "generatedEmails.job.removeError": "Не удалось убрать задачу",
    "generatedEmails.job.requestRefund": "Запросить возврат токенов",
    "generatedEmails.job.refundPrompt": "Опишите, почему считаете, что сбой произошёл по нашей вине (необязательно):",
    "generatedEmails.job.refundSubmitted": "Запрос на возврат отправлен. Мы рассмотрим его вручную.",
    "generatedEmails.job.refundError": "Не удалось отправить запрос на возврат",
    "generatedEmails.job.refundPending": "Возврат на рассмотрении",
    "generatedEmails.job.refundReturned": "Токены возвращены",
    "result.label.subject": "Тема",
    "result.editor.upload": "Загрузить с компьютера",
    "result.editor.textColor": "Цвет текста",
    "result.editor.background": "Фон",
    "result.editor.fontSize": "Размер шрифта (px)",
    "result.editor.ctaButton": "Кнопка CTA",
    "result.editor.pageBackground": "Фон страницы",
    "result.editor.backgroundColor": "Цвет фона",
    "result.editor.image": "Изображение",
    "result.editor.heading": "Заголовок",
    "result.editor.body": "Текст",
    "result.editor.bodyHtml": "Текст {n} (HTML)",
    "result.editor.footer": "Подвал",
    "result.editor.noBackground": "Без фона",
    "generatedEmails.col.actions": "",
    "page.title.privacy": "smart-letters — Политика конфиденциальности",
    "page.title.terms": "smart-letters — Условия использования",
    "page.title.verifyEmail": "smart-letters — Подтверждение email",
    "privacy.title": "Политика конфиденциальности",
    "privacy.updated": "Обновлено: 2026-05-15",
    "privacy.p1": "Мы собираем данные аккаунта (email), сессионные/защитные логи, данные профиля компании и сгенерированный контент писем для предоставления сервиса.",
    "privacy.p2": "Мы обрабатываем данные для работы аккаунта, генерации контента, защиты платформы и выполнения юридических обязательств.",
    "privacy.p3": "Мы используем сторонних обработчиков, включая AI-провайдеров, сервисы отправки писем и инфраструктурные/хранилищные сервисы.",
    "privacy.p4": "Вы можете запросить доступ/экспорт/удаление данных аккаунта через поддержку или доступные инструменты в продукте.",
    "privacy.p5": "Сроки хранения ограничены настройками retention для логов/сессий/задач; для сохранённых писем срок может быть больше, если вы не удалите их раньше.",
    "privacy.p6": "Мы храним баланс токенов, записи биллинга, запросы на возврат и оценку репутации для работы оплаты и правил контента. См. <a href=\"terms.html#tokens\">политику токенов и возвратов</a>.",
    "privacy.contact": "Контакт: support@taskflock.local",
    "terms.title": "Условия использования",
    "terms.updated": "Обновлено: 2026-05-15",
    "terms.p1": "Используя smart-letters, вы соглашаетесь использовать сервис законно и не отправлять запрещённый или вредоносный контент.",
    "terms.p2": "Вы несёте ответственность за соответствие рассылок применимым законам (включая требования по согласию/отписке, где это необходимо).",
    "terms.p3": "Вы обязаны предоставлять корректные данные аккаунта и хранить учётные данные в безопасности.",
    "terms.p4": "Мы можем ограничить или приостановить доступ при злоупотреблениях, рисках безопасности или нарушениях закона.",
    "terms.p5": "Сервис предоставляется по модели as-is/as-available и может изменяться в пределах технических ограничений.",
    "terms.tokens.title": "Токены, возвраты и репутация",
    "terms.tokens.p1": "Генерации расходуют токены: 10 за текст письма и 20 за одно изображение (или его перегенерацию). Подписка даёт ежемесячный пакет токенов; дополнительные токены можно купить по тарифу плана. На бесплатном плане — ограниченное число генераций в день без токенов.",
    "terms.tokens.p2": "При сбое по нашей вине (ошибка сервера) токены возвращаются автоматически. При нарушении правил контента (например, запрещённый запрос к изображению) токены не возвращаются.",
    "terms.tokens.p3": "Вы можете запросить ручную проверку возврата за неудачную генерацию. Мы рассматриваем запросы и принимаем решение по усмотрению.",
    "terms.tokens.p4": "Каждое нарушение снижает репутацию. Ниже 40 — без изображений и без возвратов. При 0 — генерация заблокирована до нового биллинг-периода. Восстановление: +10 каждые 24 ч (кроме 0); оплата подписки — до 100.",
    "terms.contact": "Контакт: support@taskflock.local",
    "verify.title": "Подтверждение email",
    "verify.verifying": "Проверяем ваш email…",
    "verify.goLogin": "Перейти ко входу",
    "verify.backRegister": "Назад к регистрации",
    "verify.tokenMissing": "Отсутствует токен подтверждения.",
    "verify.success": "Email успешно подтверждён. Теперь можно войти.",
    "verify.failed": "Не удалось подтвердить email.",
    "account.title": "Настройки аккаунта",
    "account.profile.title": "Профиль",
    "account.label.avatar": "Фото профиля",
    "account.avatar.hint": "JPEG, PNG, WebP или GIF с вашего компьютера.",
    "account.placeholder.email": "Email",
    "account.placeholder.displayName": "Отображаемое имя",
    "account.placeholder.avatarUrl": "URL аватара (необязательно при загрузке файла)",
    "account.button.saveProfile": "Сохранить профиль",
    "account.password.title": "Пароль",
    "account.placeholder.currentPassword": "Текущий пароль",
    "account.placeholder.newPassword": "Новый пароль",
    "account.button.changePassword": "Сменить пароль",
    "account.sessions.title": "Сессии",
    "account.sessions.revoke": "Отозвать",
    "account.sessions.current": "Текущая",
    "account.sessions.logoutCurrent": "Выйти",
    "account.sessions.unknownAgent": "Неизвестно",
    "account.subscription.title": "Подписка",
    "account.subscription.note": "Управление подпиской будет добавлено на следующем этапе. Платные лимиты включаются, когда в настройках профиля <code>subscriptionActive</code> установлено в <code>true</code> (например, администратором в базе данных); изменить это поле из этой формы нельзя.",
    "account.button.deleteAccount": "Удалить аккаунт",
    "account.confirm.deleteAccount": "Удалить аккаунт и все данные?",
    "account.error.load": "Не удалось загрузить аккаунт",
    "account.error.upload": "Не удалось загрузить файл",
    "account.error.saveProfile": "Не удалось сохранить профиль",
    "account.error.password": "Не удалось сменить пароль",
    "account.error.delete": "Не удалось удалить аккаунт",
    "status.step.queued": "В очереди…",
    "status.step.text": "Текст и варианты письма (модель ИИ)",
    "status.step.image": "Картинка для шапки письма",
    "status.step.saving": "Сохранение результата",
    "status.step.done": "Готово",
    "status.step.error": "Ошибка",
    "status.error.poll": "Не удалось получить статус",
    "generations.col.remaining": "Осталось",
    "generations.remaining.done": "—",
    "generations.remaining.unknown": "…",
    "generations.remainingEta": "~{seconds} с",
    "generations.title": "Статусы генерации",
    "generations.subtitle": "Все запуски генерации писем. Список обновляется автоматически, пока есть активные задачи.",
    "generations.empty": "Пока нет задач генерации. Запустите создание письма на шаге шаблонов.",
    "generations.col.started": "Начато",
    "generations.col.subject": "Тема",
    "generations.col.template": "Шаблон",
    "generations.col.status": "Статус",
    "generations.col.step": "Шаг",
    "generations.col.error": "Ошибка",
    "generations.action.continue": "К редактору",
    "generations.badge.queued": "В очереди",
    "generations.badge.running": "Выполняется",
    "generations.badge.done": "Готово",
    "generations.badge.error": "Ошибка",
    "common.loading": "Загрузка…",
    "common.back": "Назад",
    "page.title.payments": "smart-letters — Токены и оплата",
    "payments.title": "Токены и оплата",
    "payments.subtitle": "Оплата через PayPal (sandbox или live — по настройкам сервера). Баланс хранится только на сервере.",
    "payments.policyLink": "Политика токенов и возвратов",
    "payments.plan.tokensPerMonth": "{n} токенов в месяц",
    "payments.plan.costPerGen": "Текст {text} · изображение {image} токенов за генерацию",
    "payments.plan.freeLine": "Бесплатный план: 1 генерация в день (без токенов)",
    "payments.plan.refineLine": "Правки расходуют токены ({n} за правку)",
    "payments.status.loading": "Загрузка…",
    "payments.status.summary": "Баланс: {bal} токенов · бесплатно сегодня: {free} · {per} за генерацию",
    "payments.status.errorLoad": "Не удалось загрузить статус оплаты",
    "payments.status.errorBilling": "Ошибка оплаты",
    "payments.button.buy": "Купить через PayPal",
    "payments.button.buyMore": "Добавить токены",
    "payments.button.redirecting": "Перенаправление…",
    "payments.error.init": "Не удалось инициализировать оплату",
    "payments.error.noUrl": "PayPal не вернул ссылку подтверждения",
    "account.subtitle": "Профиль, сессии и безопасность.",
    "account.danger.title": "Опасная зона",
    "account.plan.loading": "Загрузка…",
    "account.plan.summary": "Баланс: {bal} · текст {text} · изображение {image} · бесплатно сегодня: {free} · {sub} · репутация: {rep}/100",
    "company.label.senderEmail": "Email отправителя",
    "company.label.senderName": "Имя отправителя",
    "company.button.verifySender": "Подтвердить отправителя",
    "company.sender.verified": "Отправитель подтверждён",
    "company.sender.notVerified": "Отправитель не подтверждён",
    "company.sender.checking": "Проверка…",
    "company.sender.verifyFailed": "Не удалось подтвердить отправителя",
    "company.status.saved": "Сохранено",
    "company.logo.alt": "Логотип",
    "legal.backHome": "На главную",
    "login.resendVerification.append": " Письмо для подтверждения отправлено повторно.",
  },
  en: {
    "nav.company": "Company Information",
    "nav.generate": "Generate New Email",
    "nav.generated": "Emails & Status",
    "nav.generations": "Generation status",
    "nav.account": "Account Settings",
    "nav.templates": "Templates",
    "nav.logoPlaceholder": "Logo",
    "nav.help": "Need help?",
    "nav.logout": "Log out",
    "nav.tokens": "{n} tokens",
    "nav.reputation": "Reputation",
    "nav.reputation.hint.orange": "Below 40: no image generation. Refunds disabled.",
    "nav.reputation.hint.blocked": "At 0: generation locked until your next billing period.",
    "plan.freeHint": "Free: {left} of {limit} generations left today · {balance} tokens",
    "plan.tokenHint": "{balance} tokens · text {text} · image {image} (up to {per} with image)",
    "account.tokens.title": "Tokens",
    "account.tokens.upgrade": "Upgrade plan",
    "account.tokens.buy": "Buy more tokens",
    "account.plan.subscribed": "subscription active",
    "account.plan.notSubscribed": "no subscription",
    "page.title.plans": "smart-letters — Plans",
    "plans.title": "Upgrade plan",
    "plans.subtitle": "Start on Free or upgrade to Pro for monthly tokens and top-ups.",
    "plans.free.generationsPerDay": "{n} generations per day without tokens",
    "plans.free.noTokens": "No monthly tokens or top-ups",
    "plans.free.default": "Default",
    "plans.status.onFree": "You are on the Free plan",
    "plans.empty": "No plans configured",
    "plans.includedTokens": "{n} tokens per month",
    "plans.pricingBreakdown": "Generation: {text} text · {image} image",
    "plans.extraTokenRate": "Extra tokens: {price} each",
    "plans.button.subscribe": "Subscribe",
    "plans.button.active": "Current plan",
    "plans.status.choose": "Choose a plan and pay with PayPal",
    "plans.status.subscribed": "Active plan: {plan}",
    "page.title.buyTokens": "smart-letters — Buy tokens",
    "buyTokens.title": "Buy more tokens",
    "buyTokens.subtitle": "Top up your balance at your plan rate after subscribing.",
    "buyTokens.label.amount": "Token amount",
    "buyTokens.pricePreview": "{tokens} tokens · {price}",
    "buyTokens.rateLine": "Rate: {price} per token · balance: {bal}",
    "buyTokens.needSubscription": "Subscribe on the plans page first.",
    "buyTokens.ready": "Enter an amount and pay with PayPal.",
    "buyTokens.button.buy": "Pay with PayPal",
    "buyTokens.link.plans": "Need a subscription? Upgrade plan",
    "buyTokens.success": "Tokens added to your balance.",
    "buyTokens.captureFailed": "Payment received but crediting failed — contact support.",
    "templates.cost.paid": "Cost: {total} tokens (text {text} + image {image}) · balance {bal}",
    "templates.cost.insufficient": "Need {total} tokens (text {text} + image {image}) · balance {bal}",
    "templates.cost.freeSlot": "Will use today's free generation",
    "templates.cost.toggleTotal": "{n} tokens",
    "templates.cost.toggleFree": "0 tokens (free)",
    "templates.cost.tokens": "{n} tok.",
    "templates.cost.label": "You'll pay",
    "templates.cost.selectTemplate": "Select a template",
    "templates.cost.lineText": "Email text",
    "templates.cost.lineImage": "Image",
    "templates.cost.lineTotal": "Total",
    "templates.cost.lineFree": "Free",
    "templates.cost.noImages": "Image unavailable (reputation {rep})",
    "templates.cost.blocked": "Generation unavailable (reputation 0)",
    "landing.title": "smart-letters",
    "landing.description": "AI-powered email generation service. Create an email in minutes, choose the best variant, and download the result.",
    "landing.button.login": "Sign in",
    "company.title": "Company details",
    "company.subtitle": "Fill in the data that will be used to generate emails.",
    "company.hint": "<strong>Required fields:</strong> company name, niche and other important company information, description of products or services.<br /><strong>Optional fields:</strong> logo, company website, email, company social media.",
    "company.label.name": "Company name *",
    "company.label.niche": "Company niche and other important information *",
    "company.label.description": "Description of products or services *",
    "company.label.logo": "Logo (optional)",
    "company.label.email": "Company email (optional)",
    "company.label.phone": "Phone (optional)",
    "company.label.website": "Company website (optional)",
    "company.label.socials": "Company social media (optional)",
    "company.label.comments": "Comments or wishes",
    "company.placeholder.socials": "Links separated by commas",
    "company.button.next": "Next",
    "company.button.saving": "Saving…",
    "company.error.selectImage": "Please select an image",
    "company.error.name": "Enter company name",
    "company.error.niche": "Enter niche",
    "company.error.description": "Enter product or service description",
    "company.error.save": "Save error",
    "params.title": "Email parameters",
    "params.subtitle": "Set the email topic and key parameters.",
    "params.hint": "<strong>Email parameters:</strong> what to write about, image wishes, link for the button.",
    "params.label.subject": "What to write about *",
    "params.label.imageWishes": "Image wishes",
    "params.label.ctaLink": "Link for the button",
    "params.placeholder.imageWishes": "Style, theme, colors",
    "params.placeholder.cta": "https://…",
    "params.label.colorScheme": "Email color scheme",
    "params.option.notSelected": "Not selected",
    "params.option.light": "Light",
    "params.option.dark": "Dark",
    "params.option.brand": "Brand",
    "params.button.next": "Next",
    "params.button.back": "Back",
    "params.error.subject": "Please specify what to write about",
    "landing.title": "smart-letters",
    "landing.description": "AI-powered email generation service. Create an email in minutes, pick the best variant, and download the result.",
    "landing.button.login": "Sign in",
    "login.title": "Sign in",
    "login.button": "Sign in",
    "login.label.email": "Email",
    "login.label.password": "Password",
    "login.footer.noaccount": "No account?",
    "login.footer.create": "Create",
    "login.footer.home": "Home",
    "login.error": "Sign-in error",
    "login.resendVerification": "Resend verification email",
    "login.resendVerification.sent": "Verification email sent.",
    "register.title": "Create an account",
    "register.button": "Sign up",
    "register.label.email": "Email",
    "register.label.password": "Password",
    "register.legalConsent": "I agree to the <a href=\"terms.html\" target=\"_blank\" rel=\"noopener\">Terms of Service</a> and <a href=\"privacy.html\" target=\"_blank\" rel=\"noopener\">Privacy Policy</a>.",
    "register.footer.hasaccount": "Already have an account?",
    "register.footer.login": "Sign in",
    "templates.title": "Choose a template",
    "templates.subtitle": "Choose one template to generate emails, then click \"Generate\".",
    "templates.button.generate": "Generate emails",
    "templates.button.generating": "Generating…",
    "templates.button.back": "Back",
    "templates.error.load": "Failed to load templates",
    "templates.error.generate": "Generation error",
    "templates.empty": "No templates found.",
    "templates.loading": "Loading templates…",
    "templates.preview.head": "Template preview",
    "templates.preview.showStructure": "Show structure",
    "templates.preview.hideStructure": "Hide structure",
    "template.t1": "Classic",
    "template.t2": "Minimalist",
    "template.t3": "Bright Call-to-Action",
    "template.t4": "Modern Card",
    "template.m1": "Welcome (blocks)",
    "template.m2": "B2B SaaS",
    "template.m3": "Promo",
    "template.m4": "Corporate",
    "template.m5": "Shop",
    "template.custom": "Custom layout",
    "templates.modularBadge": "Blocks",
    "templates.button.builder": "Block builder",
    "builder.title": "Email builder",
    "builder.subtitle": "Assemble your email from blocks, then generate content with AI.",
    "builder.palette": "Blocks",
    "builder.layout": "Email structure",
    "builder.preview": "Preview",
    "builder.addBlock": "Add",
    "builder.emptyLayout": "Add blocks from the palette on the left.",
    "builder.useLayout": "Use for generation",
    "builder.backTemplates": "Back to templates",
    "builder.moveUp": "Up",
    "builder.moveDown": "Down",
    "builder.remove": "Remove",
    "builder.loadPreset": "Load preset",
    "builder.previewSubject": "Your email subject",
    "builder.previewBody": "<p>AI-generated email text will appear here after generation.</p>",
    "builder.previewCta": "Learn more",
    "page.title.builder": "smart-letters — Builder",
    "editor.block.header": "Header",
    "editor.block.hero": "Hero",
    "editor.block.heroSplit": "Hero: text + image",
    "editor.block.heroCompact": "Compact banner",
    "editor.block.text": "Text",
    "editor.block.quote": "Quote",
    "editor.block.cta": "Button",
    "editor.block.ctaBanner": "CTA banner",
    "editor.block.footer": "Footer",
    "editor.block.imageFull": "Full-width image",
    "editor.block.imageLeft": "Image left",
    "editor.block.imageRight": "Image right",
    "editor.block.benefits": "Benefits",
    "editor.block.promo": "Promo",
    "editor.block.products": "Products",
    "editor.block.divider": "Divider",
    "editor.block.spacer": "Spacer",
    "editor.block.gallery": "Gallery",
    "editor.block.articleList": "Article list",
    "editor.block.videoPreview": "Video preview",
    "editor.block.featureList": "Feature list",
    "editor.block.iconText": "Icons with text",
    "editor.block.statistics": "Statistics",
    "editor.block.socialProof": "Social proof",
    "editor.block.testimonials": "Testimonials",
    "editor.block.caseStudy": "Case study",
    "editor.block.clientLogos": "Client logos",
    "editor.block.team": "Team",
    "editor.block.employee": "Team member",
    "editor.block.productCard": "Product card",
    "editor.block.pricingTable": "Pricing table",
    "editor.block.serviceCard": "Service card",
    "editor.block.faq": "FAQ",
    "editor.block.timeline": "Timeline",
    "editor.block.coupon": "Coupon",
    "editor.noFields": "No editable fields.",
    "editor.aiImage": "AI image variant",
    "editor.imageVariant": "Image",
    "editor.variant": "Variant",
    "editor.ctaLabel": "Button text",
    "editor.ctaLink": "Link URL",
    "editor.align": "Align",
    "editor.default": "Default",
    "page.title.myTemplates": "smart-letters — My templates",
    "myTemplates.title": "Email templates",
    "myTemplates.subtitle": "Create, edit, and reuse layouts for generation.",
    "myTemplates.builtin": "Built-in",
    "myTemplates.saved": "My templates",
    "myTemplates.create": "Create template",
    "myTemplates.edit": "Edit",
    "myTemplates.use": "Use for generation",
    "myTemplates.delete": "Delete",
    "myTemplates.empty": "No saved templates yet.",
    "myTemplates.deleteConfirm": "Delete this template?",
    "myTemplates.blocks": "{n} blocks",
    "myTemplates.save": "Save template",
    "myTemplates.namePlaceholder": "Template name",
    "myTemplates.nameRequired": "Enter a template name",
    "myTemplates.chooseForGeneration": "Choose for generation",
    "common.error.saveFailed": "Save failed",
    "common.error.previewFailed": "Preview failed",
    "common.error.loadFailed": "Failed to load data",
    "common.error.templateLimit": "Saved template limit reached",
    "compose.title": "Assemble the email",
    "compose.subtitle": "Swipe each block left/right or use arrows to pick variants.",
    "compose.text.clickToEdit": "Click the email body below to edit it in place (saved when you leave the field or go to the result).",
    "compose.section.image": "Image",
    "compose.section.text": "Email text",
    "compose.section.cta": "Button (CTA)",
    "compose.aria.image": "Select image",
    "compose.aria.text": "Select text",
    "compose.aria.cta": "Select button",
    "compose.empty.text": "No email data. Start by choosing a template.",
    "compose.empty.link": "Choose template",
    "compose.button.edit": "Request edits",
    "compose.button.result": "Go to result",
    "result.title": "Final email",
    "result.subtitle": "Edit on the left, full preview on the right.",
    "result.subtitleNew": "Only sections in your email are shown. Preview updates live.",
    "result.editor.hint": "Each section below matches a block in your email. Expand a section to edit it.",
    "result.editor.loading": "Loading email sections…",
    "result.subtitleLong": "Download the email to use in any mailing service.",
    "result.button.download": "Download email",
    "result.button.downloading": "Downloading…",
    "result.button.save": "Save to current email",
    "result.button.saveCopy": "Save as copy",
    "result.button.saving": "Saving…",
    "result.button.back": "Back to emails",
    "result.empty.text": "No email data.",
    "result.empty.link": "Choose template",
    "result.error.noSession": "No session for export. Return to templates.",
    "result.error.download": "Download error",
    "result.error.noEmailSelected": "This is a new email. Open a saved one or use Save as copy.",
    "result.error.save": "Failed to save email",
    "result.copy.prompt": "Enter copy name",
    "result.copy.defaultName": "Email copy",
    "result.copy.saved": "Copy saved",
    "result.image.alt": "Image",
    "result.logo.alt": "Logo",
    "result.label.imageVariant": "Image variant",
    "result.label.textVariant": "Text variant",
    "result.label.ctaVariant": "CTA variant",
    "result.label.textHtml": "Email text (HTML)",
    "result.label.ctaLabel": "CTA label",
    "result.label.ctaHref": "CTA link",
    "modal.edit.title": "Request edits",
    "modal.edit.subtitle": "Fill in only the fields you want to change. Empty field means no change.",
    "modal.edit.label.image": "Image edits",
    "modal.edit.label.text": "Email text edits",
    "modal.edit.label.cta": "Button edits",
    "modal.edit.submit": "Submit",
    "modal.edit.cancel": "Cancel",
    "theme.toggle": "Toggle theme",
    "theme.day": "Day",
    "theme.night": "Night",
    "page.title.login": "smart-letters — Sign In",
    "page.title.register": "smart-letters — Register",
    "page.title.company": "smart-letters — Company",
    "page.title.params": "smart-letters — Parameters",
    "page.title.templates": "smart-letters — Templates",
    "page.title.compose": "smart-letters — Compose",
    "page.title.result": "smart-letters — Result",
    "page.title.landing": "smart-letters",
    "page.title.generatedEmails": "smart-letters — Emails & Status",
    "page.title.account": "smart-letters — Account settings",
    "page.title.generations": "smart-letters — Generation jobs",
    "nav.langSwitch": "Switch language",
    "common.error": "Error",
    "register.error": "Registration error",
    "register.success.verify": "Registration successful. Check your email and verify your account before signing in.",
    "generatedEmails.title": "Emails and generation status",
    "generatedEmails.subtitle": "Active generation jobs and saved email history.",
    "generatedEmails.empty": "No saved emails yet.",
    "generatedEmails.placeholder.title": "Title",
    "generatedEmails.placeholder.tags": "Tags (comma separated)",
    "generatedEmails.favorite.on": "★ Favorite",
    "generatedEmails.favorite.off": "☆ Favorite",
    "generatedEmails.button.open": "Open",
    "generatedEmails.button.delete": "Delete",
    "generatedEmails.confirm.delete": "Delete this email?",
    "generatedEmails.error.load": "Failed to load generated emails",
    "generatedEmails.error.invalidId": "Invalid email id in list",
    "generatedEmails.error.update": "Failed to update",
    "generatedEmails.error.saveDetails": "Failed to save details",
    "generatedEmails.error.open": "Failed to open",
    "generatedEmails.error.delete": "Failed to delete",
    "generatedEmails.metaSubject": "Subject",
    "generatedEmails.metaTemplate": "Template",
    "generatedEmails.col.type": "Type",
    "generatedEmails.ctaNew": "Create an email",
    "generatedEmails.filter.subject": "Subject",
    "generatedEmails.filter.subjectPlaceholder": "Search subject...",
    "generatedEmails.filter.template": "Template",
    "generatedEmails.filter.status": "Status",
    "generatedEmails.filter.from": "From",
    "generatedEmails.filter.to": "To",
    "generatedEmails.filter.errorOnly": "Error only",
    "generatedEmails.filter.all": "All",
    "generatedEmails.filter.no": "No",
    "generatedEmails.filter.yes": "Yes",
    "generatedEmails.emptyRows": "No rows found.",
    "generatedEmails.type.job": "Job",
    "generatedEmails.type.email": "Email",
    "generatedEmails.menu.actions": "Actions",
    "generatedEmails.job.retry": "Retry",
    "generatedEmails.job.remove": "Remove",
    "generatedEmails.job.confirmRemove": "Remove this failed generation from the list?",
    "generatedEmails.job.retryError": "Failed to retry job",
    "generatedEmails.job.removeError": "Failed to remove job",
    "generatedEmails.job.requestRefund": "Request token refund",
    "generatedEmails.job.refundPrompt": "Explain why you believe this failure was on our side (optional):",
    "generatedEmails.job.refundSubmitted": "Refund request submitted. We will review it manually.",
    "generatedEmails.job.refundError": "Could not submit refund request",
    "generatedEmails.job.refundPending": "Refund under review",
    "generatedEmails.job.refundReturned": "Tokens returned",
    "result.label.subject": "Subject",
    "result.editor.upload": "Upload from PC",
    "result.editor.textColor": "Text color",
    "result.editor.background": "Background",
    "result.editor.fontSize": "Font size (px)",
    "result.editor.ctaButton": "CTA button",
    "result.editor.pageBackground": "Page background",
    "result.editor.backgroundColor": "Background color",
    "result.editor.image": "Image",
    "result.editor.heading": "Heading",
    "result.editor.body": "Body",
    "result.editor.bodyHtml": "Body {n} (HTML)",
    "result.editor.footer": "Footer",
    "result.editor.noBackground": "No background",
    "generatedEmails.col.actions": "Actions",
    "page.title.privacy": "smart-letters — Privacy Policy",
    "page.title.terms": "smart-letters — Terms of Service",
    "page.title.verifyEmail": "smart-letters — Verify Email",
    "privacy.title": "Privacy Policy",
    "privacy.updated": "Last updated: 2026-05-15",
    "privacy.p1": "We collect account data (email), session/security logs, company profile inputs, and generated email content to provide the service.",
    "privacy.p2": "We process data to operate your account, generate content, secure the platform, and meet legal obligations.",
    "privacy.p3": "We use third-party processors such as AI providers, email delivery providers, and infrastructure/storage services.",
    "privacy.p4": "You can request access/export/deletion of your account data via support or in-product account controls where available.",
    "privacy.p5": "Retention is limited by configured time windows for logs/sessions/jobs, and longer for saved generated emails unless deleted earlier by you.",
    "privacy.p6": "We store token balances, billing ledger entries, refund review requests, and account reputation scores to operate billing and enforce content policy. See our <a href=\"terms.html#tokens\">token &amp; refund policy</a>.",
    "privacy.contact": "Contact: support@taskflock.local",
    "terms.title": "Terms of Service",
    "terms.updated": "Last updated: 2026-05-15",
    "terms.p1": "By using smart-letters, you agree to use the service lawfully and not submit prohibited or harmful content.",
    "terms.p2": "You are responsible for compliance of outreach emails with applicable laws (including consent/unsubscribe requirements where needed).",
    "terms.p3": "You must provide accurate account information and keep your credentials secure.",
    "terms.p4": "We may suspend accounts for abuse, security risks, or legal violations.",
    "terms.p5": "The service is provided on an as-available basis, subject to updates and operational limits.",
    "terms.tokens.title": "Tokens, refunds & reputation",
    "terms.tokens.p1": "Generations use tokens: 10 for email text and 20 for one image (or image regeneration). Subscriptions include monthly tokens; you may buy extra tokens at your plan rate. The free plan includes a limited number of daily generations without tokens.",
    "terms.tokens.p2": "If a generation fails due to a server-side error on our platform, tokens are returned automatically. If a generation fails because your input violates content policy, tokens are not refunded.",
    "terms.tokens.p3": "You may submit a refund review request for a failed generation. We review requests manually and approve or deny them at our discretion.",
    "terms.tokens.p4": "Each violation lowers reputation. Below 40: no images and no refunds. At 0: generation locked until the next billing period. Recovery: +10 every 24h (except at 0); subscription payment restores to 100.",
    "terms.contact": "Contact: support@taskflock.local",
    "verify.title": "Email verification",
    "verify.verifying": "Verifying your email…",
    "verify.goLogin": "Go to login",
    "verify.backRegister": "Back to register",
    "verify.tokenMissing": "Verification token is missing.",
    "verify.success": "Email verified successfully. You can sign in now.",
    "verify.failed": "Could not verify email.",
    "account.title": "Account settings",
    "account.profile.title": "Profile",
    "account.label.avatar": "Profile photo",
    "account.avatar.hint": "JPEG, PNG, WebP, or GIF from your computer.",
    "account.placeholder.email": "Email",
    "account.placeholder.displayName": "Display name",
    "account.placeholder.avatarUrl": "Avatar URL (optional if you upload)",
    "account.button.saveProfile": "Save profile",
    "account.password.title": "Password",
    "account.placeholder.currentPassword": "Current password",
    "account.placeholder.newPassword": "New password",
    "account.button.changePassword": "Change password",
    "account.sessions.title": "Sessions",
    "account.sessions.revoke": "Revoke",
    "account.sessions.current": "Current",
    "account.sessions.logoutCurrent": "Log out",
    "account.sessions.unknownAgent": "Unknown",
    "account.subscription.title": "Subscription",
    "account.subscription.note": "Subscription management will be added in the next phase. Paid limits are enabled when <code>subscriptionActive</code> is set to <code>true</code> in your profile settings (for example by an administrator in the database); it cannot be toggled from this form.",
    "account.button.deleteAccount": "Delete account",
    "account.confirm.deleteAccount": "Delete account and all data?",
    "account.error.load": "Failed to load account",
    "account.error.upload": "Upload failed",
    "account.error.saveProfile": "Failed to save profile",
    "account.error.password": "Failed to change password",
    "account.error.delete": "Failed to delete account",
    "status.step.queued": "Queued…",
    "status.step.text": "Email copy and variants (AI model)",
    "status.step.image": "Header image",
    "status.step.saving": "Saving your result",
    "status.step.done": "Done",
    "status.step.error": "Error",
    "status.error.poll": "Could not fetch status",
    "generations.col.remaining": "Remaining",
    "generations.remaining.done": "—",
    "generations.remaining.unknown": "…",
    "generations.remainingEta": "~{seconds} s",
    "generations.title": "Generation jobs",
    "generations.subtitle": "All email generation runs. The list refreshes automatically while any job is still running.",
    "generations.empty": "No generation jobs yet. Start from the templates step.",
    "generations.col.started": "Started",
    "generations.col.subject": "Subject",
    "generations.col.template": "Template",
    "generations.col.status": "Status",
    "generations.col.step": "Step",
    "generations.col.error": "Error",
    "generations.action.continue": "Continue to editor",
    "generations.badge.queued": "Queued",
    "generations.badge.running": "Running",
    "generations.badge.done": "Done",
    "generations.badge.error": "Error",
    "common.loading": "Loading…",
    "common.back": "Back",
    "page.title.payments": "smart-letters — Tokens & billing",
    "payments.title": "Tokens & billing",
    "payments.subtitle": "Pay with PayPal (sandbox or live per server config). Your balance is stored securely on the server.",
    "payments.policyLink": "Token & refund policy",
    "payments.plan.tokensPerMonth": "{n} tokens per month",
    "payments.plan.costPerGen": "Text {text} · image {image} tokens per generation",
    "payments.plan.freeLine": "Free plan: 1 generation per day (no tokens used)",
    "payments.plan.refineLine": "Refinements use tokens ({n} each)",
    "payments.status.loading": "Loading…",
    "payments.status.summary": "Balance: {bal} tokens · {free} free left today · {per} per generation",
    "payments.status.errorLoad": "Could not load billing status",
    "payments.status.errorBilling": "Billing error",
    "payments.button.buy": "Buy with PayPal",
    "payments.button.buyMore": "Add more tokens",
    "payments.button.redirecting": "Redirecting…",
    "payments.error.init": "Payment initialization failed",
    "payments.error.noUrl": "No PayPal approval URL returned",
    "account.subtitle": "Manage profile, sessions, and security.",
    "account.danger.title": "Danger zone",
    "account.plan.loading": "Loading…",
    "account.plan.summary": "Balance: {bal} · text {text} · image {image} · {free} free today · {sub} · reputation: {rep}/100",
    "company.label.senderEmail": "Sender email",
    "company.label.senderName": "Sender name",
    "company.button.verifySender": "Verify sender",
    "company.sender.verified": "Sender verified",
    "company.sender.notVerified": "Sender not verified",
    "company.sender.checking": "Checking…",
    "company.sender.verifyFailed": "Sender verification failed",
    "company.status.saved": "Saved",
    "company.logo.alt": "Logo",
    "legal.backHome": "Home",
    "login.resendVerification.append": " Verification email re-sent.",
  },
};

window.t = function t(key, vars){
  const lang = (typeof Store !== "undefined" && Store.getLanguage) ? Store.getLanguage() : "ru";
  const dict = (typeof I18N !== "undefined" && I18N[lang]) ? I18N[lang] : {};
  const fallback = (typeof I18N !== "undefined" && I18N.en) ? I18N.en : {};
  let s = dict[key] ?? fallback[key] ?? key;
  if(vars && typeof vars === "object"){
    Object.keys(vars).forEach((k) => {
      s = s.replace(new RegExp("\\{" + k + "\\}", "g"), String(vars[k]));
    });
  }
  return s;
};

window.blockI18nKey = function blockI18nKey(name) {
  const aliases = { text_quote: "editor.block.quote", product_grid: "editor.block.products" };
  if (aliases[name]) return aliases[name];
  const camel = String(name || "").replace(/_([a-z])/g, (_, c) => c.toUpperCase());
  return "editor.block." + camel;
};

window.blockDisplayName = function blockDisplayName(name) {
  const key = blockI18nKey(name);
  const v = t(key);
  return v !== key ? v : name;
};

window.escHtml = function escHtml(s) {
  return String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
};

window.applyTranslations = function applyTranslations(){
  try{
    const lang = Store.getLanguage ? Store.getLanguage() : "ru";
    const dict = I18N[lang] || {};
    document.documentElement.lang = lang;

    // Update page title if it has a data-page-title attribute
    const pageTitleKey = document.documentElement.getAttribute("data-page-title");
    if(pageTitleKey && dict[pageTitleKey]){
      document.title = dict[pageTitleKey];
    }

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      if(!key || el.hasAttribute("data-i18n-skip")) return;
      const val = dict[key];
      if(!val) return;
      const tag = el.tagName;
      if(tag === "INPUT" || tag === "TEXTAREA"){
        if(el.hasAttribute("placeholder") || el.getAttribute("type") === "text" || el.getAttribute("type") === "email" || el.getAttribute("type") === "url" || el.getAttribute("type") === "password"){
          el.setAttribute("placeholder", val);
        }else{
          el.value = val;
        }
      }else if(tag === "OPTION"){
        el.textContent = val;
      }else{
        el.textContent = val;
      }
    });

    document.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const key = el.getAttribute("data-i18n-html");
      if(!key) return;
      const val = dict[key];
      if(!val) return;
      el.innerHTML = val;
    });
    window.dispatchEvent(new CustomEvent("taskflock-translations-applied"));
  }catch(e){
    // ignore translation errors
  }
};

// Apply saved theme/language and render global switchers
(function(){
  try{
    const currentTheme = Store.getTheme();
    Store.setTheme(currentTheme);

    /** Help link target — replace with your docs or support URL. */
    const HELP_URL = "mailto:support@taskflock.app?subject=smart-letters%20help";

    /**
     * Sidebar wide logos: paths relative to site root (e.g. "assets/nav-logo-light.svg").
     * Day = light UI, night = dark UI. If only one is set, it is used for both themes.
     * Leave both empty for the dashed "Logo" placeholder.
     */
    const NAV_LOGO_SRC_LIGHT = "assets/nav-logo-light.png";
    const NAV_LOGO_SRC_DARK = "assets/nav-logo-dark.png";
    const NAV_LOGO_ALT = "smart-letters";

    function navLogoLightUrl(){
      return (NAV_LOGO_SRC_LIGHT && String(NAV_LOGO_SRC_LIGHT).trim()) || "";
    }
    function navLogoDarkUrl(){
      return (NAV_LOGO_SRC_DARK && String(NAV_LOGO_SRC_DARK).trim()) || "";
    }
    function resolveNavLogoSrc(){
      const light = navLogoLightUrl();
      const dark = navLogoDarkUrl();
      if(Store.getTheme() === "dark"){
        return dark || light || "";
      }
      return light || dark || "";
    }
    function updateNavLogoImage(){
      const img = document.querySelector(".dashboard-nav-brand .dashboard-nav-logo-img");
      if(!img) return;
      const next = resolveNavLogoSrc();
      if(next) img.src = next;
    }

    function ensureDashboardNavLayout(nav){
      if(nav.querySelector(".dashboard-nav-brand")) return;
      const snapshot = Array.from(nav.children);
      const brand = document.createElement("div");
      brand.className = "dashboard-nav-brand";
      const hasLogo = !!(navLogoLightUrl() || navLogoDarkUrl());
      if(hasLogo){
        const logoImg = document.createElement("img");
        logoImg.className = "dashboard-nav-logo-img";
        logoImg.src = resolveNavLogoSrc();
        logoImg.alt = NAV_LOGO_ALT;
        logoImg.decoding = "async";
        logoImg.loading = "lazy";
        brand.appendChild(logoImg);
      }else{
        const logoPh = document.createElement("div");
        logoPh.className = "dashboard-nav-logo-placeholder";
        logoPh.setAttribute("data-i18n", "nav.logoPlaceholder");
        brand.appendChild(logoPh);
      }

      const links = document.createElement("div");
      links.className = "dashboard-nav-links";
      snapshot.forEach((ch) => links.appendChild(ch));

      const bottom = document.createElement("div");
      bottom.className = "dashboard-nav-bottom";

      nav.appendChild(brand);
      nav.appendChild(links);
      nav.appendChild(bottom);
    }

    const switchers = document.createElement("div");
    switchers.className = "dashboard-nav-switchers";

    // Theme button
    const themeBtn = document.createElement("button");
    themeBtn.type = "button";
    themeBtn.className = "dashboard-nav-icon-btn";
    const lang0 = Store.getLanguage();
    const dict0 = I18N[lang0] || {};
    themeBtn.setAttribute("aria-label", dict0["theme.toggle"] || "Toggle theme");

    function updateThemeLabel(){
      const t = Store.getTheme();
      const l = Store.getLanguage();
      const d = I18N[l] || {};
      const text = t === "dark" ? (d["theme.night"] || "Night") : (d["theme.day"] || "Day");
      themeBtn.textContent = text;
    }

    themeBtn.addEventListener("click", () => {
      const next = Store.getTheme() === "dark" ? "light" : "dark";
      Store.setTheme(next);
      updateThemeLabel();
      updateNavLogoImage();
    });

    updateThemeLabel();
    switchers.appendChild(themeBtn);

    // Language button
    const langBtn = document.createElement("button");
    langBtn.type = "button";
    langBtn.className = "dashboard-nav-icon-btn";
    function langSwitchAria(){
      const l = Store.getLanguage();
      const d = I18N[l] || {};
      langBtn.setAttribute("aria-label", d["nav.langSwitch"] || "Switch language");
    }
    langSwitchAria();

    function updateLangLabel(){
      const lang = Store.getLanguage();
      langBtn.textContent = lang === "en" ? "EN" : "RU";
    }

    langBtn.addEventListener("click", () => {
      const next = Store.getLanguage() === "en" ? "ru" : "en";
      Store.setLanguage(next);
      updateLangLabel();
      langSwitchAria();
      applyTranslations();
      updateThemeLabel();
      try{
        window.dispatchEvent(new CustomEvent("taskflock-language-changed", { detail: { lang: next } }));
      }catch(_e){}
    });

    updateLangLabel();
    switchers.appendChild(langBtn);

    const helpLink = document.createElement("a");
    helpLink.className = "dashboard-nav-foot-link";
    helpLink.href = HELP_URL;
    helpLink.setAttribute("data-i18n", "nav.help");
    helpLink.rel = "noopener noreferrer";

    const reputationMeter = document.createElement("div");
    reputationMeter.className = "dashboard-nav-reputation";
    reputationMeter.id = "nav-reputation";
    reputationMeter.innerHTML = '<div class="dashboard-nav-reputation-label"><span data-i18n="nav.reputation">Reputation</span><span class="dashboard-nav-reputation-score" id="nav-rep-score">—</span></div><div class="dashboard-nav-reputation-track-wrap"><div class="dashboard-nav-reputation-track" aria-hidden="true"><div class="dashboard-nav-reputation-marker" id="nav-rep-marker" style="left:100%"></div></div></div><p class="dashboard-nav-reputation-hint" id="nav-rep-hint" style="display:none"></p>';

    function updateReputationMeter(ent){
      const wrap = document.getElementById("nav-reputation");
      if(!wrap) return;
      const scoreEl = document.getElementById("nav-rep-score");
      const marker = document.getElementById("nav-rep-marker");
      const hint = document.getElementById("nav-rep-hint");
      const score = Math.max(0, Math.min(100, Number(ent?.reputationScore ?? 100)));
      const zone = ent?.reputationZone || "good";
      if(scoreEl) scoreEl.textContent = score + "/100";
      if(marker) marker.style.left = score + "%";
      wrap.classList.remove("is-orange", "is-blocked");
      if(zone === "orange") wrap.classList.add("is-orange");
      if(zone === "blocked") wrap.classList.add("is-blocked");
      if(hint){
        if(zone === "orange"){
          hint.style.display = "";
          hint.textContent = t("nav.reputation.hint.orange");
        }else if(zone === "blocked"){
          hint.style.display = "";
          hint.textContent = t("nav.reputation.hint.blocked");
        }else{
          hint.style.display = "none";
          hint.textContent = "";
        }
      }
    }

    const userCard = document.createElement("div");
    userCard.className = "dashboard-nav-user";

    const profileLink = document.createElement("a");
    profileLink.className = "dashboard-nav-user-profile";
    profileLink.href = "account-settings.html";

    const avatarWrap = document.createElement("div");
    avatarWrap.className = "dashboard-nav-user-avatar";

    const avatarImg = document.createElement("img");
    avatarImg.className = "dashboard-nav-user-avatar-img";
    avatarImg.alt = "";
    avatarImg.style.display = "none";

    const avatarPh = document.createElement("span");
    avatarPh.className = "dashboard-nav-user-avatar-ph";
    avatarPh.setAttribute("aria-hidden", "true");

    avatarWrap.appendChild(avatarImg);
    avatarWrap.appendChild(avatarPh);

    const meta = document.createElement("div");
    meta.className = "dashboard-nav-user-meta";
    const userNameEl = document.createElement("div");
    userNameEl.className = "dashboard-nav-user-name";
    userNameEl.textContent = "…";
    const userEmailEl = document.createElement("div");
    userEmailEl.className = "dashboard-nav-user-email";
    const userTokensEl = document.createElement("div");
    userTokensEl.className = "dashboard-nav-user-tokens";
    meta.appendChild(userNameEl);
    meta.appendChild(userEmailEl);
    meta.appendChild(userTokensEl);

    profileLink.appendChild(avatarWrap);
    profileLink.appendChild(meta);

    const logoutBtn = document.createElement("button");
    logoutBtn.type = "button";
    logoutBtn.className = "dashboard-nav-logout";
    logoutBtn.setAttribute("data-i18n", "nav.logout");
    logoutBtn.addEventListener("click", () => logout());

    userCard.appendChild(profileLink);
    userCard.appendChild(logoutBtn);

    async function hydrateNavUser(){
      const card = document.querySelector(".dashboard-nav-user");
      if(!card || !Store.getToken()) return;
      const nameEl = card.querySelector(".dashboard-nav-user-name");
      const emailEl = card.querySelector(".dashboard-nav-user-email");
      const tokensEl = card.querySelector(".dashboard-nav-user-tokens");
      const img = card.querySelector(".dashboard-nav-user-avatar-img");
      const ph = card.querySelector(".dashboard-nav-user-avatar-ph");
      if(!nameEl || typeof API === "undefined" || !API.getAccount) return;
      try{
        const acc = await API.getAccount();
        const email = (acc && acc.email) ? String(acc.email) : "";
        const dn = (acc && acc.displayName) ? String(acc.displayName).trim() : "";
        const display = dn || (email ? email.split("@")[0] : "—");
        nameEl.textContent = display;
        if(emailEl) emailEl.textContent = email;
        if(tokensEl){
          const bal = Number(acc?.entitlements?.tokenBalance ?? 0);
          const lang = Store.getLanguage ? Store.getLanguage() : "en";
          const dict = (typeof I18N !== "undefined" && I18N[lang]) ? I18N[lang] : {};
          const tpl = dict["nav.tokens"] || "{n} tokens";
          tokensEl.textContent = tpl.replace("{n}", bal.toLocaleString());
        }
        if(img && ph){
          const url = acc && acc.avatarUrl ? String(acc.avatarUrl).trim() : "";
          if(url){
            img.src = url;
            img.alt = display;
            img.style.display = "block";
            ph.style.display = "none";
            ph.textContent = "";
          }else{
            img.removeAttribute("src");
            img.style.display = "none";
            ph.style.display = "flex";
            ph.textContent = (display.charAt(0) || "?").toUpperCase();
          }
        }
        if(acc?.entitlements) updateReputationMeter(acc.entitlements);
      }catch{
        nameEl.textContent = "—";
        if(emailEl) emailEl.textContent = "";
        if(tokensEl) tokensEl.textContent = "";
        if(img && ph){
          img.style.display = "none";
          ph.style.display = "flex";
          ph.textContent = "?";
        }
        updateReputationMeter(null);
      }
    }
    window.refreshDashboardNavUser = hydrateNavUser;
    window.updateReputationMeter = updateReputationMeter;
    window.addEventListener("taskflock-language-changed", () => {
      if(typeof refreshDashboardNavUser === "function") void refreshDashboardNavUser();
    });

    function ensureTemplatesNavLink(nav){
      const links = nav.querySelector(".dashboard-nav-links") || nav;
      if(links.querySelector('a[href="my-templates.html"]')) return;
      const el = document.createElement("a");
      el.href = "my-templates.html";
      el.setAttribute("data-i18n", "nav.templates");
      el.textContent = "Templates";
      const after = links.querySelector('a[href="company.html"]');
      if(after && after.nextSibling) after.parentNode.insertBefore(el, after.nextSibling);
      else links.prepend(el);
    }

    const init = () => {
      const nav = document.querySelector(".dashboard-nav");
      if(nav){
        ensureTemplatesNavLink(nav);
        document.body.classList.add("has-sidebar");
        if(nav.parentElement !== document.body){
          document.body.prepend(nav);
        }
        ensureDashboardNavLayout(nav);
        const bottom = nav.querySelector(".dashboard-nav-bottom");
        if(bottom && !bottom.querySelector(".dashboard-nav-switchers")){
          if(!bottom.querySelector("#nav-reputation")){
            bottom.appendChild(reputationMeter);
          }
          bottom.appendChild(userCard);
          bottom.appendChild(switchers);
          bottom.appendChild(helpLink);
        }
        void hydrateNavUser();
        const page = (location.pathname.split("/").pop() || "").toLowerCase();
        nav.querySelectorAll("a[href]").forEach((a) => {
          if(a.classList.contains("dashboard-nav-foot-link")) return;
          const href = (a.getAttribute("href") || "").toLowerCase();
          if(href && page.endsWith(href)){
            a.classList.add("active");
          }else{
            a.classList.remove("active");
          }
        });
      }else if(!document.body.querySelector(".dashboard-nav-switchers")){
        const fallback = document.createElement("div");
        fallback.className = "dashboard-nav-floating-controls";
        fallback.appendChild(switchers);
        document.body.appendChild(fallback);
      }
      applyTranslations();
    };

    if(document.readyState === "loading"){
      document.addEventListener("DOMContentLoaded", init);
    }else{
      init();
    }
  }catch(e){
    // ignore errors in theme/lang setup
  }
})();