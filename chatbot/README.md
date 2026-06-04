# ИИ-чат-бот для сайта — настройка бэкенда (Cloudflare Worker)

Бот работает: **виджет на сайте → Worker (хранит ключи) → Claude / ChatGPT API**.
Админ-режим умеет публиковать статьи в блог через **GitHub API** (→ авто-деплой).
Все ключи лежат в секретах Worker и на сайт не попадают.

## Возможности
- Выбор провайдера (Anthropic/OpenAI) и модели — прямо в чате.
- **Публичный режим** — FAQ для посетителей (про карты).
- **Админ-режим** (по паролю) — знает внутрянку блога/оркестры + кнопка «Написать статью» (бот сам публикует статью в блог).

## Что понадобится
- API-ключ **Anthropic** (`sk-ant-...`) — console.anthropic.com (баланс пополнен).
- API-ключ **OpenAI** (`sk-...`) — platform.openai.com (баланс пополнен).
- **GitHub fine-grained токен** — github.com → Settings → Developer settings → Fine-grained tokens:
  - Repository access: **Only select repositories** → `cards-blog`.
  - Permissions → **Contents: Read and write**. Скопировать токен (`github_pat_...`).
- Пароль для админ-режима — придумать самому.
- Бесплатный аккаунт Cloudflare.

## Шаги

### 1. Создать Worker
dash.cloudflare.com → **Workers & Pages** → **Create Worker** → имя `cardsabroad-chat` → **Deploy** →
**Edit code** → вставить содержимое [`worker.js`](worker.js) → **Deploy**.

### 2. Добавить 4 секрета
Worker → **Settings** → **Variables and Secrets** → для каждого: **Add** → тип **Secret** → **Deploy**:

| Имя | Значение |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `OPENAI_API_KEY` | `sk-...` |
| `ADMIN_PASSWORD` | твой пароль для админ-режима |
| `GITHUB_TOKEN` | `github_pat_...` (Contents: R/W на cards-blog) |

### 3. (Рекомендуется) Лимит по IP
**Storage & Databases → KV** → Create namespace `chat-rate-limit`.
Worker → Settings → **Bindings** → Add → KV namespace: переменная `RATE_LIMIT` → namespace `chat-rate-limit` → Deploy.

### 4. Защита бюджета
- Anthropic и OpenAI: задать **месячные лимиты трат** в биллинге.
- В коде уже: лимит токенов, длины, числа сообщений, лимит по IP.

### 5. Скопировать адрес Worker
`https://cardsabroad-chat.ВАШ-ПОДДОМЕН.workers.dev` — передать его для подключения виджета.

## Проверка
```
curl -X POST https://cardsabroad-chat.ВАШ.workers.dev \
  -H "Content-Type: application/json" -H "Origin: https://slavasaharov93-dotcom.github.io" \
  -d '{"provider":"anthropic","model":"claude-haiku-4-5","messages":[{"role":"user","content":"Какая карта для подписок?"}]}'
```
Ответ — JSON `{"reply":"..."}`.

## Настройки в коде (worker.js)
- `PROVIDERS` — список моделей (модели OpenAI поправь под свой аккаунт).
- `PUBLIC_CONTEXT` / `ADMIN_CONTEXT` — что бот знает (каталог карт / внутрянку блога).
- При смене цен или появлении новых моделей — отредактировать и нажать **Deploy**.

## Стоимость
Haiku / gpt-4o-mini — доли цента за сообщение; генерация статьи — несколько центов.
Cloudflare Worker — бесплатного тарифа хватает (100 000 запросов/день).
