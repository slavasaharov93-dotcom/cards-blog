# HANDOFF — текущее состояние проекта

Конспект для продолжения работы (в т.ч. для Claude Code на новом компе — **прочитай этот файл для контекста проекта**).

**Живой сайт:** https://slavasaharov93-dotcom.github.io/cards-blog/
**Репозиторий:** github.com/slavasaharov93-dotcom/cards-blog

## Что это
Сайт **CardsAbroad** — оформление зарубежных карт Visa/Mastercard для россиян. Статический генератор на чистом Python (`build.py`), публикуется на GitHub Pages.

## Как устроено
- **Исходники:** `build.py` (генератор всех страниц), `offers.json` (каталог 19 карт), `articles/*.json` (блог), `assets/` — `styles.css` (дизайн) + **`custom.css`/`custom.js` (мой слой правок поверх дизайна — НЕ писать в styles.css, его затирает обновление дизайна)**, `static/` (robots.txt, sitemap.xml), `chatbot/` (бэкенд ИИ-бота).
- **Сборка:** `python build.py` → `dist/`. Просмотр: `python serve.py 8000` (или `ЗАПУСТИТЬ-САЙТ.bat`).
- **Публикация:** `git push` в `main` → GitHub Action собирает → ветка `gh-pages` → живой сайт обновляется сам (~1 мин).
- **`secrets.json`** (НЕ в git, в `.gitignore`): токен Telegram-бота для форм заявок. Создаётся из `secrets.example.json`. build.py подставляет токен при сборке; в CI берётся из GitHub Secret.

## Страницы (все генерятся билдерами в build.py)
Главная, Карты и цены, Услуги, Подписки, О нас, Заявка; страны — Казахстан/Кыргызстан/Таджикистан; платёжные системы — Visa/Mastercard/UnionPay; блог (из `articles/`).

## Фишки
- Мега-меню «Карты» (страны / системы / инструменты), флаги картинками (flagcdn).
- Главная: 3D-карта (наклон+переворот), квиз-подбор карты, калькулятор стоимости владения (курс $ авто-тянется из ЦБ РФ: cbr-xml-daily.ru).
- SEO-тексты на страновых и платёжных страницах; sitemap/robots; тёмная/светлая тема; адаптив.
- Формы заявок уходят в Telegram.

## Что осталось / в работе
- **ИИ-чат-бот.** Код готов: `chatbot/worker.js` (Cloudflare Worker — Claude + ChatGPT с выбором, публичный + админ-режим по паролю, умеет публиковать статьи в блог через GitHub API). **Не активирован.** Чтобы включить: развернуть Worker по `chatbot/README.md`, задать секреты (ANTHROPIC_API_KEY и др.), получить адрес `*.workers.dev`, вписать его в `build.py` → `CHATBOT_WORKER_URL`, запушить. Виджет чата появится на сайте (сейчас скрыт, т.к. URL пустой).
- TODO: в build.py контакты-заглушки (телефон `+7 (495) 000-00-00`, `info@cardsabroad.ru`) — заменить на реальные.

## Настроить на новом компе (офис)
1. `git clone https://github.com/slavasaharov93-dotcom/cards-blog.git`
2. Установить Python 3.x (галочка «Add Python to PATH»), если нет.
3. Создать `secrets.json` (скопировать файл с другого компа, или из `secrets.example.json` + вписать токен Telegram).
4. Запуск: `python build.py` → `python serve.py 8000`, либо `ЗАПУСТИТЬ-САЙТ.bat`.

## Рабочий цикл
Правка исходника → `git add .` → `git commit -m "..."` → `git push` → сайт обновляется сам.
