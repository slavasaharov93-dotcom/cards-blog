# ИИ-чат-бот для сайта — настройка бэкенда (Cloudflare Worker)

Бот работает по схеме: **виджет на сайте → Worker (хранит ключ) → Claude API**.
Ключ Anthropic лежит в секрете Worker и на сайт не попадает.

## Что понадобится
- API-ключ Anthropic (`sk-ant-...`) — с console.anthropic.com, пополненный баланс.
- Бесплатный аккаунт Cloudflare — dash.cloudflare.com.

## Шаги

### 1. Создать Worker
1. dash.cloudflare.com → **Workers & Pages** → **Create** → **Create Worker**.
2. Имя, например `cardsabroad-chat` → **Deploy**.
3. **Edit code** → удалить шаблон, вставить содержимое [`worker.js`](worker.js) → **Deploy**.

### 2. Добавить ключ как секрет
1. Worker → **Settings** → **Variables and Secrets**.
2. **Add** → тип **Secret** → имя `ANTHROPIC_API_KEY`, значение — твой ключ `sk-ant-...` → **Deploy**.

### 3. (Рекомендуется) Лимит запросов по IP
1. **Storage & Databases** → **KV** → **Create namespace**, имя `chat-rate-limit`.
2. Worker → **Settings** → **Bindings** → **Add** → **KV namespace**:
   - Variable name: `RATE_LIMIT`
   - KV namespace: `chat-rate-limit` → **Deploy**.
   (Без этого бот тоже работает, просто без лимита по IP.)

### 4. Защита бюджета (важно)
- В консоли Anthropic → **Billing** → задать **месячный лимит трат** (spend limit).
- В коде уже стоят: `MAX_TOKENS=512`, лимит длины и числа сообщений, лимит по IP.

### 5. Скопировать адрес Worker
В обзоре Worker будет адрес вида `https://cardsabroad-chat.ВАШ-ПОДДОМЕН.workers.dev`.
**Этот адрес нужен виджету на сайте** — передай его, чтобы подключить чат.

## Проверка
В консоли Worker (**Logs** или **Quick edit → Preview**) или командой:
```
curl -X POST https://cardsabroad-chat.ВАШ.workers.dev \
  -H "Content-Type: application/json" \
  -H "Origin: https://slavasaharov93-dotcom.github.io" \
  -d '{"messages":[{"role":"user","content":"Какая карта для оплаты подписок?"}]}'
```
Должен вернуться JSON вида `{"reply":"..."}`.

## Обновление каталога
Цены/карты бот берёт из переменной `SITE_CONTEXT` в `worker.js`. При смене цен —
обновить этот текст и заново нажать **Deploy**.

## Стоимость
Модель `claude-haiku-4-5` — порядка долей цента за сообщение. Cloudflare Worker —
бесплатного тарифа хватает с запасом (100 000 запросов/день).
