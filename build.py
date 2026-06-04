# -*- coding: utf-8 -*-
"""
Статический генератор блога «Зарубежные карты для россиян 2026».
Без внешних зависимостей. Читает статьи из articles/*.json,
рендерит сайт в dist/.

Запуск:  python build.py
"""
import json
import html
import os
import re
import shutil
import sys
from pathlib import Path

# Консоль Windows бывает в cp1251 — переключаем вывод на UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
ARTICLES_DIR = ROOT / "articles"
ASSETS_DIR = ROOT / "assets"
OFFERS_FILE = ROOT / "offers.json"
DIST = ROOT / "dist"

SITE_NAME = "CardsAbroad"
SITE_TAGLINE = "Зарубежные карты для россиян — 2026"
SITE_DESC = ("Оформление зарубежных банковских карт для россиян в 2026 году: "
             "Visa и Mastercard разных стран, удалённо, с гарантией. Каталог, цены, заявка онлайн.")

# --- Коммерческие настройки (ЗАМЕНИТЕ на свои данные перед публикацией) ---
CONTACTS = {
    "phone": "+7 (495) 000-00-00",
    "phone_href": "tel:+74950000000",
    "email": "info@cardsabroad.ru",
    "telegram": "https://t.me/Razdor_Razdor",
    "telegram_label": "@Razdor_Razdor",
    "whatsapp": "https://wa.me/70000000000",
    "hours": "Ежедневно 10:00–20:00 (МСК)",
}
# Куда отправлять заявки с форм. Подставьте URL сервиса (Formspree/Getform/свой бэкенд).
# Если пусто — форма работает в демо-режиме (показывает «спасибо», ничего не отправляя).
FORM_ENDPOINT = ""

# Telegram-бот для приёма заявок.
# ВАЖНО: токен НЕ хранится в этом файле (он публичный — уходит в репозиторий и в JS сайта).
# Значения берутся из переменной окружения или из локального secrets.json (он в .gitignore).
#   Пример secrets.json:  {"TELEGRAM_BOT_TOKEN": "7123456789:AAH...", "TELEGRAM_CHAT_ID": "12345"}
#   Получить токен: @BotFather → /newbot. chat_id: https://api.telegram.org/bot<ТОКЕН>/getUpdates
# Пока значения пустые — форма работает в демо-режиме.
def _secret(key, default=""):
    if os.environ.get(key):
        return os.environ[key]
    try:
        with open(ROOT / "secrets.json", encoding="utf-8") as f:
            return json.load(f).get(key, default) or default
    except (FileNotFoundError, ValueError):
        return default

TELEGRAM_BOT_TOKEN = _secret("TELEGRAM_BOT_TOKEN")  # бот @cardabroadbot
TELEGRAM_CHAT_ID = _secret("TELEGRAM_CHAT_ID")      # чат @Razdor_Razdor

# Адрес Cloudflare Worker для ИИ-чат-бота. Пусто — виджет чата НЕ показывается.
# После развёртывания Worker вставьте сюда https://...workers.dev (см. chatbot/README.md).
CHATBOT_WORKER_URL = ""

# Категории применения карт
USE_CASES = {
    "travel": "Путешествия",
    "subscribe": "Подписки и онлайн",
    "swift": "SWIFT-переводы",
    "freelance": "Фриланс и доход",
}

# ---------------------------------------------------------------------------
# Мини-конвертер Markdown -> HTML (поддержка: заголовки, списки, таблицы,
# цитаты, hr, жирный/курсив/код, ссылки, абзацы).
# ---------------------------------------------------------------------------

def _inline(text):
    """Инлайн-разметка. text уже НЕ экранирован — экранируем здесь."""
    # Защитим инлайн-код, чтобы внутри ничего не парсилось.
    placeholders = []

    def stash(m):
        placeholders.append(m.group(1))
        return f"\x00{len(placeholders) - 1}\x00"

    text = re.sub(r"`([^`]+)`", stash, text)
    text = html.escape(text, quote=False)

    # ссылки [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" '
                  f'rel="noopener">{m.group(1)}</a>',
        text,
    )
    # жирный **...** и __...__
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__([^_]+)__", r"<strong>\1</strong>", text)
    # курсив *...* и _..._
    text = re.sub(r"(?<!\*)\*(?!\*)([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"(?<!_)_(?!_)([^_]+)_(?!_)", r"<em>\1</em>", text)

    # вернём инлайн-код
    def unstash(m):
        code = html.escape(placeholders[int(m.group(1))], quote=False)
        return f"<code>{code}</code>"

    text = re.sub(r"\x00(\d+)\x00", unstash, text)
    return text


def _slugify_anchor(text):
    t = re.sub(r"<[^>]+>", "", text).strip().lower()
    t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", "-", t)
    return t or "section"


def md_to_html(md):
    lines = md.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)

    def is_table_sep(s):
        return bool(re.match(r"^\s*\|?[\s:|-]+\|?\s*$", s)) and "-" in s

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # пустая строка
        if not stripped:
            i += 1
            continue

        # горизонтальная линия
        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            out.append("<hr>")
            i += 1
            continue

        # картинка-блок:  ![подпись](src)  или  ![alt](src "подпись")
        mi = re.match(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)\s*$', line)
        if mi:
            alt = html.escape(mi.group(1), quote=True)
            src = html.escape(mi.group(2), quote=True)
            caption = mi.group(3) or mi.group(1)
            cap_html = f"<figcaption>{_inline(caption)}</figcaption>" if caption else ""
            out.append(
                f'<figure class="post-img"><img src="{src}" alt="{alt}" '
                f'loading="lazy" decoding="async">{cap_html}</figure>'
            )
            i += 1
            continue

        # заголовки
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            level = max(2, min(level, 4))  # внутри статьи только h2..h4
            content = _inline(m.group(2).strip())
            anchor = _slugify_anchor(content)
            out.append(f'<h{level} id="{anchor}">{content}</h{level}>')
            i += 1
            continue

        # таблица (есть разделитель на следующей строке)
        if "|" in line and i + 1 < n and is_table_sep(lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "".join(f"<th>{_inline(c)}</th>" for c in header)
            body = ""
            for r in rows:
                cells = "".join(f"<td>{_inline(c)}</td>" for c in r)
                body += f"<tr>{cells}</tr>"
            out.append(
                '<div class="table-wrap"><table><thead><tr>'
                f"{thead}</tr></thead><tbody>{body}</tbody></table></div>"
            )
            continue

        # цитата
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append(f"<blockquote>{_inline(' '.join(buf))}</blockquote>")
            continue

        # нумерованный список
        if re.match(r"^\s*\d+\.\s+", line):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*\d+\.\s+", "", lines[i])))
                i += 1
            lis = "".join(f"<li>{it}</li>" for it in items)
            out.append(f"<ol>{lis}</ol>")
            continue

        # маркированный список
        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*[-*+]\s+", "", lines[i])))
                i += 1
            lis = "".join(f"<li>{it}</li>" for it in items)
            out.append(f"<ul>{lis}</ul>")
            continue

        # абзац (собираем до пустой строки)
        buf = [stripped]
        i += 1
        while i < n and lines[i].strip() and not re.match(
            r"^\s*(#{1,6}\s|[-*+]\s|\d+\.\s|>|!\[[^\]]*\]\(|([-*_])\2{2,}\s*$)", lines[i]
        ) and not ("|" in lines[i] and i + 1 < n and is_table_sep(lines[i + 1])):
            buf.append(lines[i].strip())
            i += 1
        out.append(f"<p>{_inline(' '.join(buf))}</p>")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Шаблоны страниц
# ---------------------------------------------------------------------------

def chatbot_widget():
    """Виджет ИИ-чат-бота (выбор провайдера/модели, публичный + админ-режим).
    Возвращает пустую строку, если адрес Worker не задан."""
    if not CHATBOT_WORKER_URL:
        return ""
    # Обычная (не f) строка: внутри много фигурных скобок JS.
    tpl = """
<div id="aiChat">
  <button class="aichat-fab" id="aichatFab" aria-label="Чат с ИИ-консультантом">💬</button>
  <div class="aichat-panel" id="aichatPanel" hidden>
    <div class="aichat-head">
      <strong>ИИ-консультант</strong>
      <select id="aichatProvider" title="Провайдер">
        <option value="anthropic">Claude</option>
        <option value="openai">ChatGPT</option>
      </select>
      <select id="aichatModel" title="Модель"></select>
      <button class="aichat-x" id="aichatClose" aria-label="Закрыть">×</button>
    </div>
    <div class="aichat-msgs" id="aichatMsgs"></div>
    <div class="aichat-admin" id="aichatAdminRow">
      <input type="password" id="aichatPass" placeholder="Пароль администратора" autocomplete="off">
      <button id="aichatUnlock" type="button">Войти</button>
    </div>
    <div class="aichat-articlerow" id="aichatArticleRow" hidden>
      <button id="aichatWrite" type="button">✍️ Написать статью в блог</button>
    </div>
    <form class="aichat-input" id="aichatForm">
      <textarea id="aichatText" rows="1" placeholder="Спросите про карты…"></textarea>
      <button type="submit" aria-label="Отправить">▶</button>
    </form>
  </div>
</div>
<style>
#aiChat *{box-sizing:border-box}
.aichat-fab{position:fixed;left:20px;bottom:20px;z-index:9998;width:56px;height:56px;border-radius:50%;border:none;background:#2563eb;color:#fff;font-size:24px;cursor:pointer;box-shadow:0 6px 20px rgba(0,0,0,.25)}
.aichat-panel{position:fixed;left:20px;bottom:86px;z-index:9999;width:344px;max-width:calc(100vw - 40px);height:470px;max-height:calc(100vh - 120px);display:flex;flex-direction:column;background:#fff;border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.28);font-size:14px}
.aichat-head{display:flex;align-items:center;gap:6px;padding:8px 10px;background:#2563eb;color:#fff}
.aichat-head strong{margin-right:auto;font-size:14px;white-space:nowrap}
.aichat-head select{font-size:12px;border-radius:6px;border:none;padding:2px 4px;max-width:90px}
.aichat-x{background:transparent;border:none;color:#fff;font-size:22px;cursor:pointer;line-height:1;padding:0 2px}
.aichat-msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px;background:#f8fafc}
.aichat-msg{padding:8px 10px;border-radius:10px;max-width:88%;white-space:pre-wrap;line-height:1.45;word-wrap:break-word}
.aichat-msg.user{align-self:flex-end;background:#2563eb;color:#fff}
.aichat-msg.bot{align-self:flex-start;background:#fff;border:1px solid #e5e7eb;color:#111}
.aichat-admin,.aichat-articlerow{display:flex;gap:6px;padding:6px 10px;border-top:1px solid #eee}
.aichat-admin input{flex:1;padding:6px;border:1px solid #d1d5db;border-radius:6px;font-size:13px}
.aichat-admin button,.aichat-articlerow button{padding:6px 10px;border:none;border-radius:6px;background:#10b981;color:#fff;cursor:pointer;font-size:13px}
.aichat-articlerow{justify-content:center}
.aichat-articlerow button{width:100%}
.aichat-input{display:flex;gap:6px;padding:8px;border-top:1px solid #eee}
.aichat-input textarea{flex:1;resize:none;padding:8px;border:1px solid #d1d5db;border-radius:8px;font-family:inherit;font-size:14px;max-height:90px}
.aichat-input button{width:42px;border:none;border-radius:8px;background:#2563eb;color:#fff;cursor:pointer;font-size:16px}
:root[data-theme="dark"] .aichat-panel{background:#0f172a;border-color:#1e293b;color:#e5e7eb}
:root[data-theme="dark"] .aichat-msgs{background:#0b1220}
:root[data-theme="dark"] .aichat-msg.bot{background:#1e293b;border-color:#334155;color:#e5e7eb}
:root[data-theme="dark"] .aichat-admin input,:root[data-theme="dark"] .aichat-input textarea{background:#1e293b;border-color:#334155;color:#e5e7eb}
</style>
<script>
(function(){
  var URL_="__WORKER_URL__";
  var MODELS={anthropic:["claude-haiku-4-5","claude-sonnet-4-6","claude-opus-4-8"],openai:["gpt-4o-mini","gpt-4o"]};
  var LABELS={"claude-haiku-4-5":"Haiku · быстрый","claude-sonnet-4-6":"Sonnet · баланс","claude-opus-4-8":"Opus · умный","gpt-4o-mini":"gpt-4o-mini","gpt-4o":"gpt-4o"};
  var $=function(id){return document.getElementById(id);};
  var fab=$("aichatFab"),panel=$("aichatPanel"),closeB=$("aichatClose"),provSel=$("aichatProvider"),modelSel=$("aichatModel"),msgs=$("aichatMsgs"),form=$("aichatForm"),text=$("aichatText"),adminRow=$("aichatAdminRow"),passIn=$("aichatPass"),unlockB=$("aichatUnlock"),articleRow=$("aichatArticleRow"),writeB=$("aichatWrite");
  var history=[],mode="public",pass="";
  function fillModels(){var p=provSel.value;modelSel.innerHTML="";MODELS[p].forEach(function(m){var o=document.createElement("option");o.value=m;o.textContent=LABELS[m]||m;modelSel.appendChild(o);});}
  fillModels();provSel.onchange=fillModels;
  fab.onclick=function(){panel.hidden=!panel.hidden;if(!panel.hidden)text.focus();};
  closeB.onclick=function(){panel.hidden=true;};
  function addMsg(role,txt){var d=document.createElement("div");d.className="aichat-msg "+role;d.textContent=txt;msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;return d;}
  function ask(content){
    addMsg("user",content);history.push({role:"user",content:content});
    var load=addMsg("bot","…");
    fetch(URL_,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({provider:provSel.value,model:modelSel.value,mode:mode,password:pass,messages:history})})
      .then(function(r){return r.json();})
      .then(function(d){load.remove();if(d.error){addMsg("bot","⚠️ "+d.error);return;}addMsg("bot",d.reply);history.push({role:"assistant",content:d.reply});})
      .catch(function(){load.remove();addMsg("bot","⚠️ Ошибка связи. Попробуйте позже.");});
  }
  form.onsubmit=function(e){e.preventDefault();var v=text.value.trim();if(!v)return;text.value="";ask(v);};
  text.addEventListener("keydown",function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();form.requestSubmit();}});
  unlockB.onclick=function(){pass=passIn.value;if(!pass)return;mode="admin";adminRow.hidden=true;articleRow.hidden=false;addMsg("bot","🔓 Админ-режим. Спросите про работу блога/оркестры или нажмите «Написать статью». (Пароль проверяется при первом запросе.)");};
  writeB.onclick=function(){var topic=prompt("О чём написать новую статью в блог?");if(!topic)return;addMsg("user","✍️ Статья на тему: "+topic);var load=addMsg("bot","Пишу статью и публикую в блог…");
    fetch(URL_,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"write_article",provider:provSel.value,model:modelSel.value,mode:"admin",password:pass,topic:topic})})
      .then(function(r){return r.json();}).then(function(d){load.remove();addMsg("bot",d.error?("⚠️ "+d.error):d.reply);})
      .catch(function(){load.remove();addMsg("bot","⚠️ Ошибка связи.");});};
  addMsg("bot","Здравствуйте! Я ИИ-консультант по зарубежным картам. Чем помочь? 💳");
})();
</script>
"""
    return tpl.replace("__WORKER_URL__", CHATBOT_WORKER_URL)


def page_shell(title, description, body, *, active="", extra_head="", base=""):
    # base — префикс пути до корня сайта ("" для корня, "../" для /blog/*).
    nav_items = [("Главная", f"{base}index.html", "home"),
                 ("Карты и цены", f"{base}cards.html", "cards"),
                 ("Услуги", f"{base}services.html", "services"),
                 ("Подписки", f"{base}subscriptions.html", "subscriptions"),
                 ("Казахстан", f"{base}kazakhstan.html", "kazakhstan"),
                 ("Блог", f"{base}index.html#blog", "blog"),
                 ("О нас", f"{base}about.html", "about")]
    nav = "".join(
        f'<a href="{href}"{" class=\"active\"" if active == key else ""}>{label}</a>'
        for label, href, key in nav_items
    )
    chatbot = chatbot_widget()
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<link rel="icon" type="image/svg+xml" href="{base}favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Unbounded:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}styles.css">
<script src="{base}site.js" defer></script>
{extra_head}
<script>
  // Применяем тему до отрисовки, чтобы не было вспышки.
  (function () {{
    try {{
      var t = localStorage.getItem('theme');
      if (!t) t = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', t);
    }} catch (e) {{}}
  }})();
</script>
</head>
<body>
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="{base}index.html">
      <span class="brand-mark">◈</span>
      <span class="brand-text">{SITE_NAME}<small>{SITE_TAGLINE}</small></span>
    </a>
    <nav class="nav" id="site-nav">{nav}</nav>
    <div class="header-right">
      <a class="btn btn-primary btn-sm header-cta" href="{base}order.html">Оформить</a>
      <button class="theme-toggle" type="button" aria-label="Переключить тему" title="Светлая / тёмная тема">
        <span class="ic-sun">☀</span><span class="ic-moon">☾</span>
      </button>
      <button class="nav-toggle" type="button" aria-label="Меню" aria-controls="site-nav" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <div class="container footer-grid">
    <div class="footer-brand">
      <a class="brand" href="{base}index.html">
        <span class="brand-mark">◈</span>
        <span class="brand-text">{SITE_NAME}<small>{SITE_TAGLINE}</small></span>
      </a>
      <p class="muted small">Помогаем россиянам оформить рабочую зарубежную карту — удалённо и с гарантией.</p>
      <div class="footer-tg">{tg_button(base, label="Написать в Telegram", cls="btn btn-tg btn-sm")}</div>
    </div>
    <div class="footer-col">
      <h4>Разделы</h4>
      <a href="{base}cards.html">Карты и цены</a>
      <a href="{base}services.html">Услуги</a>
      <a href="{base}index.html#blog">Блог</a>
      <a href="{base}about.html">О нас</a>
      <a href="{base}order.html">Оформить заявку</a>
    </div>
    <div class="footer-col">
      <h4>Популярное</h4>
      <a href="{base}subscriptions.html">Карта для подписок</a>
      <a href="{base}kazakhstan.html">Карта Казахстана</a>
      <a href="{base}kyrgyzstan.html">Карта Кыргызстана</a>
      <a href="{base}tajikistan.html">Карта Таджикистана</a>
      <a href="{base}mastercard.html">Карта Mastercard</a>
      <a href="{base}visa.html">Карта Visa</a>
      <a href="{base}unionpay.html">Карта UnionPay</a>
      <a href="{base}cards.html#faq">Частые вопросы</a>
      <a href="{base}index.html#reviews">Отзывы</a>
      <a href="{base}index.html#guarantees">Гарантии</a>
    </div>
    <div class="footer-col">
      <h4>Контакты</h4>
      <a href="{CONTACTS['phone_href']}">{CONTACTS['phone']}</a>
      <a href="mailto:{CONTACTS['email']}">{CONTACTS['email']}</a>
      <a href="{CONTACTS['telegram']}" rel="noopener">Telegram {CONTACTS['telegram_label']}</a>
      <a href="{CONTACTS['whatsapp']}" rel="noopener">WhatsApp</a>
      <span class="muted small">{CONTACTS['hours']}</span>
    </div>
  </div>
  <div class="container footer-bottom">
    <p class="muted small">© 2026 {SITE_NAME}. Информация о картах, ценах и условиях носит
    справочный характер, актуальные условия уточняйте при оформлении заявки. Не является
    публичной офертой, юридической или финансовой консультацией.</p>
  </div>
</footer>
<a class="tg-float" href="{CONTACTS['telegram']}" rel="noopener" target="_blank" aria-label="Написать в Telegram">
  {icon("plane", 24)}<span>Telegram</span>
</a>
<script>
  window.TG_CFG = {{ token: "{TELEGRAM_BOT_TOKEN}", chat: "{TELEGRAM_CHAT_ID}" }};

  (function () {{
    var btn = document.querySelector('.theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', function () {{
      var cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try {{ localStorage.setItem('theme', next); }} catch (e) {{}}
    }});
  }})();

  // Мобильное меню (гамбургер).
  (function () {{
    var t = document.querySelector('.nav-toggle');
    var nav = document.getElementById('site-nav');
    if (!t || !nav) return;
    t.addEventListener('click', function () {{
      var open = nav.classList.toggle('open');
      t.classList.toggle('is-open', open);
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
    }});
    nav.querySelectorAll('a').forEach(function (a) {{
      a.addEventListener('click', function () {{
        nav.classList.remove('open'); t.classList.remove('is-open');
        t.setAttribute('aria-expanded', 'false');
      }});
    }});
  }})();

  // Обработка лид-форм: заявка уходит в Telegram-бот (если настроен), иначе на
  // data-endpoint, иначе — демо-режим («спасибо»).
  (function () {{
    function fieldVal(form, name) {{
      var el = form.querySelector('[name="' + name + '"]');
      return el ? (el.value || '').trim() : '';
    }}
    function buildText(form) {{
      var page = document.title;
      var lines = ['🔔 <b>Новая заявка</b> — {SITE_NAME}'];
      var map = [['name','👤 Имя'],['contact','📞 Контакт'],['card','💳 Карта'],
                 ['email','✉️ Email'],['message','💬 Комментарий']];
      map.forEach(function (m) {{
        var v = fieldVal(form, m[0]);
        if (v) lines.push(m[1] + ': ' + v.replace(/[<>]/g, ''));
      }});
      lines.push('🔗 Страница: ' + page);
      return lines.join('\\n');
    }}
    var forms = document.querySelectorAll('form.lead-form');
    forms.forEach(function (form) {{
      form.addEventListener('submit', function (e) {{
        e.preventDefault();
        // honeypot — если бот заполнил скрытое поле, делаем вид, что всё ок.
        if (fieldVal(form, '_gotcha')) {{ showOk(); return; }}
        var ok = form.querySelector('.lead-success');
        var btn = form.querySelector('button[type="submit"]');
        var endpoint = form.getAttribute('data-endpoint');
        var cfg = window.TG_CFG || {{}};
        function showOk() {{
          form.querySelectorAll('.lead-row, .lead-actions, .lead-fields').forEach(function (el) {{ el.style.display = 'none'; }});
          if (ok) ok.hidden = false;
        }}
        if (btn) {{ btn.disabled = true; btn.dataset.label = btn.textContent; btn.textContent = 'Отправляем…'; }}
        if (cfg.token && cfg.chat) {{
          fetch('https://api.telegram.org/bot' + cfg.token + '/sendMessage', {{
            method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ chat_id: cfg.chat, text: buildText(form), parse_mode: 'HTML', disable_web_page_preview: true }})
          }}).then(function () {{ showOk(); }}).catch(function () {{ showOk(); }});
        }} else if (endpoint) {{
          fetch(endpoint, {{ method: 'POST', body: new FormData(form), headers: {{ 'Accept': 'application/json' }} }})
            .then(function () {{ showOk(); }}).catch(function () {{ showOk(); }});
        }} else {{
          showOk();
        }}
      }});
    }});
  }})();

  // Фильтр каталога карт по сценарию использования.
  (function () {{
    var chips = document.querySelectorAll('[data-filter]');
    if (!chips.length) return;
    var cards = document.querySelectorAll('.offer[data-use]');
    chips.forEach(function (ch) {{
      ch.addEventListener('click', function () {{
        chips.forEach(function (c) {{ c.classList.remove('active'); }});
        ch.classList.add('active');
        var f = ch.getAttribute('data-filter');
        cards.forEach(function (card) {{
          var use = ' ' + card.getAttribute('data-use') + ' ';
          card.style.display = (f === 'all' || use.indexOf(' ' + f + ' ') >= 0) ? '' : 'none';
        }});
      }});
    }});
  }})();
</script>
{chatbot}
</body>
</html>"""


CATEGORY_CLASS = {"Обзор": "cat-overview", "Сравнение": "cat-compare", "Гайд": "cat-guide"}

# Палитры обложек по категориям: (старт, финиш, светлый акцент)
COVER_COLORS = {
    "Обзор": ("#2563eb", "#4f46e5", "#c7d2fe"),
    "Сравнение": ("#0ea5e9", "#10b981", "#bbf7d0"),
    "Гайд": ("#f59e0b", "#ef4444", "#fde68a"),
    "default": ("#475569", "#1e293b", "#cbd5e1"),
}

# Категорийный глиф (рисуется в правом верхнем углу обложки)
def _glyph(category, color):
    if category == "Обзор":  # глобус
        return (f'<g stroke="{color}" stroke-width="2.4" fill="none" opacity="0.9">'
                f'<circle cx="338" cy="52" r="22"/>'
                f'<ellipse cx="338" cy="52" rx="9" ry="22"/>'
                f'<line x1="316" y1="52" x2="360" y2="52"/>'
                f'<line x1="320" y1="40" x2="356" y2="40"/>'
                f'<line x1="320" y1="64" x2="356" y2="64"/></g>')
    if category == "Сравнение":  # столбики
        return (f'<g fill="{color}" opacity="0.92">'
                f'<rect x="316" y="56" width="9" height="20" rx="2"/>'
                f'<rect x="330" y="44" width="9" height="32" rx="2"/>'
                f'<rect x="344" y="34" width="9" height="42" rx="2"/></g>')
    if category == "Гайд":  # галочка в круге
        return (f'<g opacity="0.95"><circle cx="338" cy="52" r="22" fill="none" '
                f'stroke="{color}" stroke-width="2.4"/>'
                f'<path d="M327 53 l7 7 l13 -15" fill="none" stroke="{color}" '
                f'stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></g>')
    return ""


def cover_svg(category, uid):
    """Декоративная SVG-обложка статьи (виртуальная банковская карта)."""
    c1, c2, light = COVER_COLORS.get(category, COVER_COLORS["default"])
    glyph = _glyph(category, light)
    return f'''<svg class="cover-svg" viewBox="0 0 400 210" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/>
    </linearGradient>
    <linearGradient id="cd{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.95"/>
      <stop offset="1" stop-color="#ffffff" stop-opacity="0.72"/>
    </linearGradient>
  </defs>
  <rect width="400" height="210" fill="url(#bg{uid})"/>
  <circle cx="60" cy="180" r="90" fill="#ffffff" opacity="0.07"/>
  <circle cx="350" cy="170" r="60" fill="#ffffff" opacity="0.06"/>
  {glyph}
  <g transform="translate(34 58) rotate(-7)">
    <rect width="190" height="120" rx="16" fill="url(#cd{uid})"/>
    <rect x="20" y="26" width="34" height="26" rx="5" fill="{c1}" opacity="0.85"/>
    <path d="M62 30 a14 14 0 0 1 0 18" fill="none" stroke="{c2}" stroke-width="3" stroke-linecap="round" opacity="0.85"/>
    <path d="M70 24 a22 22 0 0 1 0 30" fill="none" stroke="{c2}" stroke-width="3" stroke-linecap="round" opacity="0.6"/>
    <rect x="20" y="74" width="120" height="7" rx="3.5" fill="{c1}" opacity="0.35"/>
    <rect x="20" y="90" width="70" height="7" rx="3.5" fill="{c1}" opacity="0.22"/>
  </g>
</svg>'''


# ---------------------------------------------------------------------------
# Коммерческие компоненты
# ---------------------------------------------------------------------------

def fmt_price(n):
    return f"{n:,}".replace(",", " ")


def img_figure(base, filename, caption, *, cls="post-img"):
    """Фото с подписью-атрибуцией Unsplash."""
    src = f"{base}assets/img/{filename}"
    cap = (f"{caption} · Фото: <a href='https://unsplash.com/' rel='noopener'>Unsplash</a>"
           if caption else "Фото: <a href='https://unsplash.com/' rel='noopener'>Unsplash</a>")
    return (f'<figure class="{cls}"><img src="{src}" alt="{html.escape(caption)}" '
            f'loading="lazy" decoding="async"><figcaption>{cap}</figcaption></figure>')


# --- Иконки (инлайн-SVG, stroke=currentColor) ---
ICONS = {
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 2.5 15.3 0 18M12 3c-2.5 2.7-2.5 15.3 0 18"/>',
    "card": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="M3 9.5h18M6.5 14.5h4"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.4-3 8.2-7 10-4-1.8-7-5.6-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    "bolt": '<path d="M13 3L5 13h6l-1 8 8-10h-6z"/>',
    "headset": '<path d="M4 13v-1a8 8 0 0 1 16 0v1"/><rect x="3" y="13" width="4" height="6" rx="1.5"/><rect x="17" y="13" width="4" height="6" rx="1.5"/><path d="M20 19a4 4 0 0 1-4 3h-2"/>',
    "wallet": '<rect x="3" y="6" width="18" height="13" rx="2.5"/><path d="M3 10h18M16 14h2"/>',
    "plane": '<path d="M10.5 13.5L3 11l2-2 6.5 1.5L16 5.5c.8-.8 2-1 2.6-.4.6.6.4 1.8-.4 2.6L13.5 12 15 18l-2 2-2.5-6.5z"/>',
    "play": '<rect x="3" y="4" width="18" height="14" rx="2.5"/><path d="M10 8l5 3-5 3z"/><path d="M8 21h8"/>',
    "swap": '<path d="M7 7h11l-3-3M17 17H6l3 3"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "ruble": '<path d="M8 4h5a4 4 0 0 1 0 8H8M8 4v16M5 12h8M5 16h6"/>',
    "lock": '<rect x="5" y="10" width="14" height="10" rx="2.5"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "star": '<path d="M12 3l2.6 5.6 6 .8-4.4 4.2 1.1 6L12 16.8 6.7 19.6l1.1-6L3.4 9.4l6-.8z"/>',
}


def icon(name, size=22):
    p = ICONS.get(name, "")
    return (f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{p}</svg>')


def tg_button(base="", label="Написать в Telegram", cls="btn btn-tg"):
    return (f'<a class="{cls}" href="{CONTACTS["telegram"]}" rel="noopener" target="_blank">'
            f'{icon("plane", 18)}<span>{html.escape(label)}</span></a>')


DEFAULT_INTEREST = ["Подберите за меня", "Казахстан", "Кыргызстан", "Армения",
                    "Турция", "Таджикистан", "Виртуальная карта (США/Гонконг)",
                    "Премиальная / SWIFT"]


def lead_form(base, *, compact=False, options=None, button="Отправить заявку"):
    """Лид-форма. compact=True — короткий вариант (имя + контакт)."""
    opts = options or DEFAULT_INTEREST
    select = "".join(f"<option>{html.escape(o)}</option>" for o in opts)
    endpoint = f' data-endpoint="{FORM_ENDPOINT}"' if FORM_ENDPOINT else ""
    if compact:
        fields = f"""<div class="lead-row">
        <label>Имя<input name="name" type="text" required placeholder="Как к вам обращаться"></label>
        <label>Телефон или Telegram<input name="contact" type="text" required placeholder="+7… или @username"></label>
      </div>"""
    else:
        fields = f"""<div class="lead-row">
        <label>Имя<input name="name" type="text" required placeholder="Как к вам обращаться"></label>
        <label>Телефон или Telegram<input name="contact" type="text" required placeholder="+7… или @username"></label>
      </div>
      <div class="lead-row">
        <label>Интересует карта<select name="card">{select}</select></label>
        <label>Email (по желанию)<input name="email" type="email" placeholder="you@example.com"></label>
      </div>
      <label class="lead-msg">Комментарий<textarea name="message" rows="3" placeholder="Например: нужна карта для оплаты подписок"></textarea></label>"""
    return f"""<form class="lead-form"{endpoint} novalidate>
      <div class="lead-fields">
        {fields}
        <input type="text" name="_gotcha" class="lead-hp" tabindex="-1" autocomplete="off" aria-hidden="true">
      </div>
      <div class="lead-actions">
        <button type="submit" class="btn btn-primary">{button}</button>
        <span class="muted small">Перезвоним и поможем выбрать. Без спама.</span>
      </div>
      <p class="lead-success" hidden>✓ Спасибо! Заявка принята — мы свяжемся с вами в ближайшее время.</p>
    </form>"""


def cta_form_section(base, *, heading="Оставьте заявку", sub="", compact=False, anchor="lead"):
    sub_html = f'<p class="muted">{html.escape(sub)}</p>' if sub else ""
    return f"""
<section id="{anchor}" class="cta-section">
  <div class="container">
    <div class="cta-card">
      <div class="cta-text">
        <span class="eyebrow">Заявка онлайн</span>
        <h2>{html.escape(heading)}</h2>
        {sub_html}
        <ul class="cta-points">
          <li>Удалённо — приезжать не нужно</li>
          <li>Подберём карту под вашу задачу</li>
          <li>Рассрочка от 990 ₽/мес</li>
        </ul>
      </div>
      <div class="cta-form">
        {lead_form(base, compact=compact)}
      </div>
    </div>
  </div>
</section>"""


STEPS = [
    ("1", "Заявка", "Оставляете заявку на сайте или в мессенджере — мы перезваниваем и подбираем карту под задачу."),
    ("2", "Оплата", "Выбираете карту и оплачиваете удобным способом, доступна рассрочка от 990 ₽/мес."),
    ("3", "Оформление", "Оформляем карту в банке-партнёре. При отказе банка возвращаем деньги."),
    ("4", "Получение", "Виртуальная — за 1 день; пластик — доставка или самовывоз. Карта готова к работе."),
]


def steps_block():
    items = "".join(
        f"""<div class="step">
        <span class="step-num">{n}</span>
        <h3>{html.escape(t)}</h3>
        <p>{html.escape(d)}</p>
      </div>""" for n, t, d in STEPS
    )
    return f"""
<section class="steps-section">
  <div class="container">
    <div class="section-head"><h2>Как это работает</h2>
      <p class="muted">От заявки до готовой карты — четыре шага.</p></div>
    <div class="steps-grid">{items}</div>
  </div>
</section>"""


def infographic_cards(cards_data):
    """Инфографика для каталога вместо стоковых фото."""
    countries = len({c["country"] for c in cards_data})
    min_price = min(c["price"] for c in cards_data)
    tiles = [
        ("globe", f"{countries} стран", "Казахстан, Кыргызстан, Армения, Турция и другие"),
        ("card", "Visa · MC · UnionPay", "Карты международных платёжных систем"),
        ("bolt", "от 1 дня", "Виртуальная — сразу, пластик — курьером"),
        ("shield", "Гарантия", "Вернём деньги, если банк отказал"),
    ]
    cells = "".join(
        f"""<div class="info-tile">
        <span class="info-ic">{icon(ic, 26)}</span>
        <b>{html.escape(v)}</b>
        <span class="muted small">{html.escape(d)}</span>
      </div>""" for ic, v, d in tiles
    )
    systems = "".join(
        f'<span class="pay-badge">{s}</span>'
        for s in ["VISA", "Mastercard", "UnionPay"]
    )
    return f"""
<section class="infographic-section">
  <div class="container">
    <div class="info-grid">{cells}</div>
    <div class="pay-row">
      <span class="muted small">Поддерживаемые системы:</span>
      <div class="pay-badges">{systems}</div>
      <span class="muted small">оплата в 150+ странах и в большинстве онлайн-сервисов</span>
    </div>
  </div>
</section>"""


GUARANTEES = [
    ("shield", "Возврат при отказе банка",
     "Если банк-партнёр отказал в открытии счёта — возвращаем оплату полностью. Вы ничем не рискуете."),
    ("lock", "Безопасность данных",
     "Не просим пароли и коды из СМС. Работаем только с официальными банками-партнёрами."),
    ("headset", "Сопровождение на всех этапах",
     "Поддержка в Telegram и WhatsApp до, во время и после оформления — поможем с активацией и пополнением."),
    ("ruble", "Прозрачные цены",
     "Стоимость карты, активацию и обслуживание показываем заранее. Без скрытых платежей и доплат."),
]


def guarantees_block(base=""):
    items = "".join(
        f"""<div class="guarantee">
        <span class="guarantee-ic">{icon(ic, 26)}</span>
        <div><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></div>
      </div>""" for ic, t, d in GUARANTEES
    )
    return f"""
<section id="guarantees" class="guarantees-section">
  <div class="container">
    <div class="section-head"><span class="eyebrow">{icon("shield",16)} Гарантии</span>
      <h2>Почему с нами безопасно</h2>
      <p class="muted">Берём риски на себя и отвечаем за результат.</p></div>
    <div class="guarantee-grid">{items}</div>
  </div>
</section>"""


REVIEWS = [
    ("Игорь М.", "Москва", 5, "Подписки",
     "Нужна была карта для Apple, Steam и ChatGPT. Оформили казахстанскую за два дня, "
     "всё работает — подписки списываются без сбоев. Помогли с активацией в мессенджере."),
    ("Анна К.", "Санкт-Петербург", 5, "Путешествия",
     "Брала карту перед поездкой в ОАЭ. Оплачивала отель, такси и кафе без проблем, "
     "конвертация выгоднее, чем думала. Спасибо за подробную консультацию."),
    ("Дмитрий В.", "Екатеринбург", 5, "Фриланс",
     "Принимаю оплату от зарубежных заказчиков. Подобрали карту со счётом и SWIFT, "
     "объяснили всё про налоги и отчётность в ФНС. Рекомендую."),
    ("Мария С.", "Казань", 4, "Подписки",
     "Долго не решалась, но менеджер всё разложил по полочкам. Карта пришла курьером, "
     "оплатила Netflix и Spotify сразу же. Небольшая задержка с доставкой, но в итоге всё ок."),
    ("Сергей Л.", "Новосибирск", 5, "SWIFT",
     "Нужны были крупные переводы за рубеж. Оформили премиальную карту со счётом, "
     "перевод прошёл без вопросов. Отдельное спасибо за сопровождение сделки."),
    ("Ольга П.", "Краснодар", 5, "Путешествия",
     "Оформила виртуальную карту за один день перед отпуском. Работает в Booking и "
     "при оплате авиабилетов. Очень удобно, что всё удалённо."),
]


def stars(n):
    full = "".join(f'<span class="star on">{icon("star",14)}</span>' for _ in range(n))
    empty = "".join(f'<span class="star">{icon("star",14)}</span>' for _ in range(5 - n))
    return f'<div class="stars">{full}{empty}</div>'


def reviews_block():
    cards = "".join(
        f"""<figure class="review">
        {stars(r)}
        <blockquote>{html.escape(txt)}</blockquote>
        <figcaption>
          <span class="review-ava">{html.escape(name[0])}</span>
          <span class="review-who"><b>{html.escape(name)}</b><span class="muted small">{html.escape(city)} · {html.escape(tag)}</span></span>
        </figcaption>
      </figure>""" for name, city, r, tag, txt in REVIEWS
    )
    return f"""
<section id="reviews" class="reviews-section">
  <div class="container">
    <div class="section-head"><span class="eyebrow">{icon("star",16)} Отзывы</span>
      <h2>Что говорят клиенты</h2>
      <p class="muted">Более 1500 оформленных карт. Средняя оценка 4.9 из 5.</p></div>
    <div class="reviews-grid">{cards}</div>
  </div>
</section>"""


FAQ = [
    ("Это легально — россиянину иметь зарубежную карту?",
     "Да. Закон не запрещает гражданам РФ открывать счета и карты в иностранных банках. "
     "Об открытии счёта нужно уведомить ФНС в течение месяца, а раз в год подавать отчёт о "
     "движении средств (ОДДС). Мы подскажем, как это сделать."),
    ("Нужно ли ехать за границу, чтобы оформить карту?",
     "В большинстве случаев — нет. Многие карты (виртуальные и часть пластиковых) оформляются "
     "удалённо. Если для конкретного банка нужна личная явка, мы предупредим заранее и предложим "
     "альтернативу."),
    ("Сколько времени занимает оформление?",
     "Виртуальную карту можно получить за 1 день. Пластиковую — обычно от нескольких дней до "
     "пары недель в зависимости от страны и способа доставки."),
    ("Что будет, если банк откажет в открытии счёта?",
     "Мы возвращаем оплату полностью. Вы ничем не рискуете — это наша гарантия."),
    ("Какие карты подойдут для оплаты подписок (Apple, Google, Steam, ChatGPT)?",
     "Подойдут карты Казахстана, Кыргызстана и виртуальные карты США/Гонконга. Они принимаются "
     "большинством зарубежных сервисов. Подберём вариант под ваши сервисы."),
    ("Как происходит оплата и есть ли рассрочка?",
     "Оплатить можно удобным способом после подбора карты. Доступна рассрочка от 990 ₽/мес. "
     "Все условия озвучиваем заранее."),
    ("Безопасно ли это? Вы просите пароли и коды?",
     "Нет. Мы никогда не запрашиваем пароли, коды из СМС и доступ к вашим российским счетам. "
     "Работаем только с официальными банками-партнёрами."),
]


def faq_block(base="", items=None, heading="Частые вопросы"):
    items = items or FAQ
    qa = "".join(
        f"""<details class="faq-item">
        <summary>{html.escape(q)}<span class="faq-plus">{icon("check",18)}</span></summary>
        <div class="faq-answer"><p>{html.escape(a)}</p></div>
      </details>""" for q, a in items
    )
    return f"""
<section id="faq" class="faq-section">
  <div class="container container-narrow">
    <div class="section-head"><span class="eyebrow">FAQ</span>
      <h2>{html.escape(heading)}</h2>
      <p class="muted">Не нашли ответ? Напишите нам в Telegram — подскажем.</p></div>
    <div class="faq-list">{qa}</div>
  </div>
</section>"""


def offer_card(base, c):
    badge = ""
    if not c.get("available", True):
        badge = '<span class="offer-badge soon">Скоро</span>'
    elif c.get("popular"):
        badge = '<span class="offer-badge hot">Хит</span>'
    feats = "".join(f"<span class='chip'>{html.escape(f)}</span>" for f in c.get("features", []))
    feats_html = f'<div class="offer-feats">{feats}</div>' if feats else ""
    uses = " ".join(c.get("useCases", []))
    cta_label = "Оформить" if c.get("available", True) else "Узнать о наличии"
    spec = lambda label, val: (f"<li><span>{label}</span><b>{html.escape(str(val))}</b></li>"
                               if val and val != "—" else "")
    specs = "".join([
        spec("Срок выпуска", c.get("processing")),
        spec("Валюты", c.get("currencies")),
        spec("Активация", c.get("activation")),
        spec("Обслуживание", c.get("fee")),
        spec("Снятие/день", c.get("withdrawal")),
        spec("Покупки/день", c.get("purchase")),
        spec("Комиссия снятия", c.get("cash")),
        spec("Срок действия", c.get("validity")),
    ])
    cls = "offer" + (" is-popular" if c.get("popular") else "") + ("" if c.get("available", True) else " is-soon")
    return f"""<article class="{cls}" data-use="{uses}">
  <div class="offer-head">
    <span class="offer-flag">{c.get('flag','💳')}</span>
    <div class="offer-headtext">
      <h3>{html.escape(c['country'])}</h3>
      <span class="offer-sub">{html.escape(c['system'])} · {html.escape(c['type'])}</span>
    </div>
    {badge}
  </div>
  <div class="offer-name">{html.escape(c['name'])}</div>
  <div class="offer-price">{fmt_price(c['price'])} ₽</div>
  <ul class="offer-specs">{specs}</ul>
  {feats_html}
  <a class="btn {'btn-primary' if c.get('available', True) else 'btn-ghost'} offer-cta" href="{base}order.html">{cta_label}</a>
</article>"""


def card(a):
    cat = a.get("category", "Статья")
    cls = CATEGORY_CLASS.get(cat, "cat-default")
    tags = "".join(f"<span class='tag'>{html.escape(t)}</span>" for t in a.get("tags", [])[:3])
    return f"""<article class="card">
  <a class="card-link" href="blog/{a['slug']}.html">
    <div class="card-cover {cls}">
      {cover_svg(cat, 'c-' + a['slug'])}
      <div class="card-cover-meta">
        <span class="card-cat">{html.escape(cat)}</span>
        <span class="card-readtime">{a.get('readingMinutes', 5)} мин</span>
      </div>
    </div>
    <div class="card-body">
      <h3>{html.escape(a['title'])}</h3>
      <p>{html.escape(a['excerpt'])}</p>
      <div class="card-tags">{tags}</div>
    </div>
    <span class="card-cta">Читать →</span>
  </a>
</article>"""


# Скрипты главной: квиз-подбор + калькулятор владения, 3D-наклон карты, плавное появление.
# CARDS — курируемые данные для калькулятора (богаче offers.json: активация/обслуживание).
# При смене цен — синхронизировать с offers.json вручную.
INDEX_SCRIPTS = """
<script>
  // ---------- Квиз-подбор + калькулятор стоимости владения ----------
  (function () {
    var CARDS = [
      { c: 'Казахстан', f: 'kz', n: 'MasterCard Standard', p: 14990, use: ['subscribe'], v: false, days: '5 дней', actU: 0, actNote: '+ доставка 20 000 ₸', fee1U: 120, fee2U: 499, feeNote: 'eResidency' },
      { c: 'Таджикистан', f: 'tj', n: 'VISA Gold', p: 21990, use: ['subscribe', 'travel'], v: false, days: '3 дня', actU: 35, fee1U: 24, fee2U: 24, feeNote: '$2/мес' },
      { c: 'Кыргызстан', f: 'kg', n: 'VISA мультивалютная (Gold/Infinite)', p: 32990, use: ['travel', 'subscribe'], v: false, days: '7–17 дней', actU: 0, fee1U: 20, fee2U: 20 },
      { c: 'Кыргызстан', f: 'kg', n: 'VISA Credit (Platinum/Signature)', p: 35990, use: ['travel', 'freelance'], v: false, days: '14 дней', actU: 0, fee1U: 150, fee2U: 150 },
      { c: 'Банк СНГ', f: null, n: 'VISA (Classic/Platinum)', p: 38990, use: ['subscribe'], v: false, days: '5–10 дней', actU: 0, fee1U: 10, fee2U: 10, feeNote: '$50 за 5 лет' },
      { c: 'Армения', f: 'am', n: 'VISA Credit (Signature/Infinite)', p: 54990, use: ['freelance', 'swift'], v: false, days: '21 день', actU: 130, fee1U: 494, fee2U: 494, feeNote: '$26/мес + $182/год' },
      { c: 'Международный банк', f: null, n: 'VISA (Platinum/Signature)', p: 64990, use: ['swift', 'freelance'], v: false, days: '21 день', actU: 0, fee1U: 220, fee2U: 220 },
      { c: 'Гонконг', f: 'hk', n: 'MasterCard Virtual', p: 9990, use: ['subscribe'], v: true, soon: true, days: '1 день', actU: 50, actNote: 'вкл. депозит $25', fee1U: 84, fee2U: 84, feeNote: '$7/мес' },
      { c: 'Турция', f: 'tr', n: 'MasterCard Standard (быстрая)', p: 19990, use: ['travel', 'subscribe'], v: false, soon: true, days: '1 день', actU: 70, fee1U: 0, fee2U: 0 }
    ];
    var BUDGET = { low: 20000, mid: 40000, any: Infinity };
    var state = { use: 'subscribe', format: 'any', budget: 'mid', term: 1 };
    var selected = null;
    var resultEl = document.getElementById('quiz-result');
    var rowsEl = document.getElementById('calc-rows');
    var rateEl = document.getElementById('calc-rate');
    if (!resultEl || !rowsEl) return;

    function fmt(n) { return Math.round(n).toLocaleString('ru-RU'); }
    function flagImg(card, size) {
      return card.f
        ? '<img src="https://flagcdn.com/' + card.f + '.svg" alt="" width="' + size + '" style="border-radius:4px;vertical-align:-3px">'
        : '<span style="font-size:' + size + 'px;line-height:1">◈</span>';
    }
    function score(card) {
      var s = 0;
      if (card.use.indexOf(state.use) >= 0) s += 3;
      if (state.format === 'virtual') s += card.v ? 2 : -4;
      if (state.format === 'plastic') s += card.v ? -4 : 1;
      s += card.p <= BUDGET[state.budget] ? 1 : -2.5;
      if (card.soon) s -= 1;
      return s - card.p / 1e7;
    }
    function pick() {
      return CARDS.slice().sort(function (a, b) { return score(b) - score(a); });
    }
    function renderResult() {
      var ranked = pick();
      var best = ranked[0];
      selected = best;
      var alts = ranked.slice(1, 3);
      var html =
        '<div class="quiz-best">' +
          '<div class="quiz-best-head">' + flagImg(best, 30) +
            '<div><b>' + best.c + ' — ' + best.n + '</b>' +
            '<span class="muted small">' + (best.v ? 'Виртуальная' : 'Пластиковая') + ' · выпуск ' + best.days + (best.soon ? ' · скоро в продаже' : '') + '</span></div>' +
          '</div>' +
          '<div class="quiz-best-price">' + fmt(best.p) + ' ₽</div>' +
          (best.soon ? '<p class="muted small">Эта карта скоро появится — оставьте заявку, забронируем условия или предложим альтернативу.</p>' : '') +
          '<div class="quiz-best-actions">' +
            '<a class="btn btn-primary" href="order.html">Оформить эту карту</a>' +
            '<a class="btn btn-ghost btn-sm" href="#calc-wrap">Стоимость владения ↓</a>' +
          '</div>' +
        '</div>' +
        '<div class="quiz-alts"><span class="muted small">Ещё подходят:</span>' +
          alts.map(function (c, i) {
            return '<button type="button" class="quiz-alt" data-i="' + CARDS.indexOf(c) + '">' + flagImg(c, 18) + ' ' + c.c + ' · ' + fmt(c.p) + ' ₽</button>';
          }).join('') +
        '</div>';
      resultEl.innerHTML = html;
      resultEl.querySelectorAll('.quiz-alt').forEach(function (b) {
        b.addEventListener('click', function () {
          selected = CARDS[+b.getAttribute('data-i')];
          renderCalc();
          document.getElementById('calc-wrap').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
      });
      renderCalc();
    }
    function renderCalc() {
      var c = selected; if (!c) return;
      var rate = Math.max(1, parseFloat(rateEl.value) || 95);
      var act = c.actU * rate;
      var fee = c.fee1U * rate + (state.term === 2 ? c.fee2U * rate : 0);
      var total = c.p + act + fee;
      var rows = [
        ['Карта «' + c.c + ' — ' + c.n + '»', fmt(c.p) + ' ₽'],
        ['Активация', (c.actU ? '$' + c.actU + ' ≈ ' + fmt(act) + ' ₽' : 'Бесплатно') + (c.actNote ? ' <span class="muted small">(' + c.actNote + ')</span>' : '')],
        ['Обслуживание, 1-й год', c.fee1U ? '$' + c.fee1U + ' ≈ ' + fmt(c.fee1U * rate) + ' ₽' + (c.feeNote ? ' <span class="muted small">(' + c.feeNote + ')</span>' : '') : 'Бесплатно']
      ];
      if (state.term === 2) rows.push(['Обслуживание, 2-й год', c.fee2U ? '$' + c.fee2U + ' ≈ ' + fmt(c.fee2U * rate) + ' ₽' : 'Бесплатно']);
      rowsEl.innerHTML = rows.map(function (r) {
        return '<div class="calc-row"><span>' + r[0] + '</span><b>' + r[1] + '</b></div>';
      }).join('') +
      '<div class="calc-row calc-total"><span>Итого за ' + (state.term === 2 ? '2 года' : '1 год') + '</span><b>≈ ' + fmt(total) + ' ₽</b></div>';
    }
    document.querySelectorAll('.quiz-opts').forEach(function (group) {
      var q = group.getAttribute('data-q');
      group.querySelectorAll('.quiz-opt').forEach(function (btn) {
        btn.addEventListener('click', function () {
          group.querySelectorAll('.quiz-opt').forEach(function (b) { b.classList.remove('active'); });
          btn.classList.add('active');
          if (q === 'term') { state.term = +btn.getAttribute('data-v'); renderCalc(); }
          else { state[q] = btn.getAttribute('data-v'); renderResult(); }
        });
      });
    });
    rateEl.addEventListener('input', renderCalc);
    renderResult();
  })();

  // ---------- 3D-карта в hero: наклон за курсором + переворот по клику ----------
  (function () {
    var wrap = document.getElementById('hero-visual');
    var card = document.getElementById('card3d');
    if (!wrap || !card) return;
    function flip() { card.classList.toggle('flipped-card'); }
    card.addEventListener('click', flip);
    card.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); flip(); }
    });
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (!matchMedia('(hover: hover)').matches) return;
    wrap.addEventListener('pointermove', function (e) {
      var r = wrap.getBoundingClientRect();
      var x = (e.clientX - r.left) / r.width - .5;
      var y = (e.clientY - r.top) / r.height - .5;
      card.style.transform = 'rotateY(' + (14 + x * 16) + 'deg) rotateX(' + (-6 - y * 14) + 'deg)';
    });
    wrap.addEventListener('pointerleave', function () { card.style.transform = ''; });
  })();

  // ---------- Плавное появление секций ----------
  (function () {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (!('IntersectionObserver' in window)) return;
    var els = document.querySelectorAll('.offer, .step, .use-card, .guarantee, .review, .card, .info-tile, .faq-item, .more-card, .trust-item, .quiz-wrap, .calc-wrap');
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('rv-in'); io.unobserve(en.target); }
      });
    }, { threshold: .12, rootMargin: '0px 0px -5% 0px' });
    els.forEach(function (el, i) {
      el.classList.add('rv');
      el.style.transitionDelay = Math.min(i % 4 * 70, 280) + 'ms';
      io.observe(el);
    });
  })();
</script>
"""


def build_index(articles, cards_data):
    blog_cards = "\n".join(card(a) for a in articles)
    avail = [c for c in cards_data if c.get("available", True)]
    min_price = min(c["price"] for c in cards_data)
    countries = len({c["country"] for c in cards_data})
    popular = [c for c in cards_data if c.get("popular") and c.get("available", True)][:4]
    pop_html = "\n".join(offer_card("", c) for c in popular)
    body = f"""
<section class="hero">
  <div class="container hero-grid">
    <div class="hero-copy">
      <span class="eyebrow">Visa и Mastercard · удалённо · с гарантией</span>
      <h1>Зарубежная карта для россиян<br><span class="grad">оформим за вас в 2026</span></h1>
      <p class="lead">Подберём и оформим рабочую карту иностранного банка под вашу задачу —
      подписки, путешествия, фриланс и SWIFT. Без выезда за границу.</p>
      <div class="hero-actions">
        <a class="btn btn-primary" href="#quiz">Подобрать карту за 30 сек</a>
        <a class="btn btn-ghost" href="#lead">Получить консультацию</a>
      </div>
    </div>
    <div class="hero-visual" id="hero-visual">
      <div class="card3d card3d-back-card" aria-hidden="true">
        <div class="card3d-face">
          <div class="card3d-row"><span class="card3d-chip"></span></div>
          <div class="card3d-num">5169 •••• •••• 8841</div>
          <div class="card3d-row card3d-foot"><span>KG · VISA GOLD</span><span>12/30</span></div>
        </div>
      </div>
      <div class="card3d" id="card3d" role="button" tabindex="0" aria-label="Перевернуть карту">
        <div class="card3d-rotor">
          <div class="card3d-face">
            <div class="card3d-row">
              <span class="card3d-chip"></span>
              <svg class="card3d-wave" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 8.5a8 8 0 0 1 0 7"/><path d="M9.5 6.5a11 11 0 0 1 0 11"/><path d="M13 4.5a14.5 14.5 0 0 1 0 15"/></svg>
            </div>
            <div class="card3d-num">4276 •••• •••• 2026</div>
            <div class="card3d-row card3d-foot">
              <span class="card3d-holder"><small>CARDHOLDER</small><b>CARDSABROAD CLIENT</b></span>
              <span class="card3d-brand">◈</span>
            </div>
            <span class="card3d-shine"></span>
          </div>
          <div class="card3d-face card3d-backface" aria-hidden="true">
            <div class="card3d-stripe"></div>
            <div class="card3d-sig"><span class="card3d-sig-line"></span><span class="card3d-cvv">•••</span></div>
            <p class="card3d-backnote">ВЫПУСКАЕТСЯ ОФИЦИАЛЬНЫМ БАНКОМ-ПАРТНЁРОМ<br>ДОСТАВКА ПО РФ · ПОДДЕРЖКА ЕЖЕДНЕВНО 10:00–20:00</p>
            <span class="card3d-fliphint">Нажмите ещё раз, чтобы вернуть ↻</span>
          </div>
        </div>
      </div>
      <div class="hero-chips">
        <div class="hero-chip hero-chip-1"><b>от {fmt_price(min_price)} ₽</b><span>цена карты</span></div>
        <div class="hero-chip hero-chip-2"><b>{countries} стран</b><span>на выбор</span></div>
        <div class="hero-chip hero-chip-3"><b>от 1 дня</b><span>срок выпуска</span></div>
      </div>
    </div>
  </div>
</section>

<section class="trust-band">
  <div class="container trust-inner">
    <div class="trust-item"><b>Удалённо</b><span>без поездок за границу</span></div>
    <div class="trust-item"><b>Гарантия возврата</b><span>если банк отказал</span></div>
    <div class="trust-item"><b>Рассрочка</b><span>от 990 ₽/мес</span></div>
    <div class="trust-item"><b>Поддержка</b><span>Telegram, WhatsApp</span></div>
  </div>
</section>

<section class="offers-section">
  <div class="container">
    <div class="section-head section-head-row">
      <div><h2>Популярные карты</h2>
        <p class="muted">Самые востребованные варианты прямо сейчас.</p></div>
      <a class="btn btn-ghost btn-sm" href="cards.html">Весь каталог →</a>
    </div>
    <div class="offers-grid">{pop_html}</div>
  </div>
</section>

<section id="quiz" class="quiz-section">
  <div class="container">
    <div class="section-head">
      <h2>Подберите карту за 30 секунд</h2>
      <p class="muted">Три вопроса — и мы покажем подходящую карту с честным расчётом стоимости владения.</p>
    </div>
    <div class="quiz-wrap">
      <div class="quiz-questions">
        <div class="quiz-q">
          <div class="quiz-label">1. Для чего нужна карта?</div>
          <div class="quiz-opts" data-q="use" role="group" aria-label="Назначение карты">
            <button type="button" class="quiz-opt active" data-v="subscribe">Подписки и сервисы</button>
            <button type="button" class="quiz-opt" data-v="travel">Путешествия</button>
            <button type="button" class="quiz-opt" data-v="freelance">Фриланс и доход</button>
            <button type="button" class="quiz-opt" data-v="swift">SWIFT-переводы</button>
          </div>
        </div>
        <div class="quiz-q">
          <div class="quiz-label">2. Какой формат удобнее?</div>
          <div class="quiz-opts" data-q="format" role="group" aria-label="Формат карты">
            <button type="button" class="quiz-opt active" data-v="any">Не важно</button>
            <button type="button" class="quiz-opt" data-v="plastic">Пластиковая</button>
            <button type="button" class="quiz-opt" data-v="virtual">Виртуальная</button>
          </div>
        </div>
        <div class="quiz-q">
          <div class="quiz-label">3. Бюджет на оформление?</div>
          <div class="quiz-opts" data-q="budget" role="group" aria-label="Бюджет">
            <button type="button" class="quiz-opt" data-v="low">До 20 000 ₽</button>
            <button type="button" class="quiz-opt active" data-v="mid">До 40 000 ₽</button>
            <button type="button" class="quiz-opt" data-v="any">Не ограничен</button>
          </div>
        </div>
      </div>
      <div class="quiz-result" id="quiz-result" aria-live="polite"></div>
    </div>
    <div class="calc-wrap" id="calc-wrap">
      <div class="calc-head">
        <h3>Стоимость владения — считаем честно</h3>
        <div class="calc-controls">
          <div class="quiz-opts" data-q="term">
            <button type="button" class="quiz-opt active" data-v="1">1 год</button>
            <button type="button" class="quiz-opt" data-v="2">2 года</button>
          </div>
          <label class="calc-rate">Курс $&nbsp;<input type="number" id="calc-rate" value="95" min="1" step="1" inputmode="numeric">&nbsp;₽</label>
        </div>
      </div>
      <div class="calc-rows" id="calc-rows"></div>
      <p class="muted small">Расчёт примерный: курс доллара задайте свой, локальные сборы (доставка, депозиты) указаны в карточке. Итоговые условия фиксируем до оплаты.</p>
    </div>
  </div>
</section>

{steps_block()}

{guarantees_block()}

{reviews_block()}

{cta_form_section("", heading="Не знаете, какая карта подойдёт?", sub="Оставьте заявку — поможем выбрать и оформить под вашу задачу.")}

{faq_block()}

<section id="blog" class="blog-section">
  <div class="container">
    <div class="section-head">
      <h2>Блог: как всё устроено</h2>
      <p class="muted">Разбираем варианты, сравниваем страны, объясняем налоги и риски.</p>
    </div>
    <div class="cards-grid">
      {blog_cards}
    </div>
  </div>
</section>
""" + INDEX_SCRIPTS
    return page_shell(f"{SITE_NAME} — оформление зарубежных карт для россиян", SITE_DESC,
                      body, active="home")


def build_article(a, articles):
    content = md_to_html(a["bodyMarkdown"])
    cat = a.get("category", "Статья")
    cls = CATEGORY_CLASS.get(cat, "cat-default")
    tags = "".join(f"<span class='tag'>{html.escape(t)}</span>" for t in a.get("tags", []))
    # читать ещё
    others = [x for x in articles if x["slug"] != a["slug"]][:2]
    more = "".join(
        f"<a class='more-card' href='{o['slug']}.html'>"
        f"<span class='more-cat'>{html.escape(o.get('category',''))}</span>"
        f"<strong>{html.escape(o['title'])}</strong></a>"
        for o in others
    )
    body = f"""
<article class="post">
  <div class="container container-narrow">
    <a class="back" href="../index.html#blog">← Все статьи</a>
    <div class="post-cover {cls}">{cover_svg(cat, 'p-' + a['slug'])}</div>
    <div class="post-meta">
      <span class="badge {cls}">{html.escape(cat)}</span>
      <span class="muted small">{a.get('readingMinutes', 5)} мин чтения</span>
    </div>
    <h1>{html.escape(a['title'])}</h1>
    <p class="post-lead">{html.escape(a['excerpt'])}</p>
    <div class="post-tags">{tags}</div>
    <hr class="post-rule">
    <div class="prose">
      {content}
    </div>
  </div>
</article>
{cta_form_section("../", heading="Нужна такая карта?", sub="Подберём и оформим под вашу задачу — удалённо, с гарантией возврата при отказе банка.", compact=True)}
<section class="more-section">
  <div class="container container-narrow">
    <h2 class="more-title">Читать дальше</h2>
    <div class="more-grid">{more}</div>
  </div>
</section>
"""
    extra = (f'<meta property="og:title" content="{html.escape(a["title"])}">'
             f'<meta property="og:type" content="article">')
    return page_shell(f"{a['title']} — {SITE_NAME}", a.get("metaDescription", a["excerpt"]),
                      body, extra_head=extra, base="../", active="blog")


def build_about():
    body = f"""
<section class="hero hero-sm">
  <div class="container container-narrow">
    <span class="eyebrow">О нас</span>
    <h1>Помогаем оформить рабочую зарубежную карту</h1>
  </div>
</section>
<section class="about-section">
  <div class="container container-narrow prose">
    <p>{SITE_NAME} — сервис, который помогает россиянам получить банковскую карту
    иностранного банка в 2026 году: подбираем подходящий вариант, сопровождаем
    оформление и доставляем карту. Параллельно ведём блог, где честно объясняем,
    как всё устроено — варианты, налоги и риски.</p>
    <h2>Почему с нами удобно</h2>
    <ul>
      <li><strong>Удалённо.</strong> Большинство карт оформляются без выезда за границу.</li>
      <li><strong>Под задачу.</strong> Подбираем карту под подписки, поездки, фриланс или SWIFT.</li>
      <li><strong>С гарантией.</strong> Если банк отказывает в открытии счёта — возвращаем деньги.</li>
      <li><strong>Прозрачно.</strong> Показываем цены и условия заранее, без скрытых платежей.</li>
    </ul>
    {img_figure("", "team.jpg", "Команда помогает подобрать и оформить карту")}
    <h2>Важно</h2>
    <p>Информация о картах, ценах и условиях носит справочный характер: тарифы и требования
    банков быстро меняются, поэтому актуальные условия мы подтверждаем при оформлении заявки.
    Материалы блога не являются юридической или финансовой консультацией.</p>
  </div>
</section>
{cta_form_section("", heading="Готовы помочь с картой", sub="Оставьте заявку — ответим и подберём вариант.")}
"""
    return page_shell(f"О нас — {SITE_NAME}", "О сервисе CardsAbroad: оформление зарубежных карт.",
                      body, active="about")


def build_cards(cards_data):
    filters = [("all", "Все")] + [(k, v) for k, v in USE_CASES.items()]
    chips = "".join(
        f'<button class="filter-chip{" active" if k == "all" else ""}" data-filter="{k}">{html.escape(v)}</button>'
        for k, v in filters
    )
    grid = "\n".join(offer_card("", c) for c in cards_data)
    min_price = min(c["price"] for c in cards_data)
    body = f"""
<section class="hero hero-sm">
  <div class="container">
    <span class="eyebrow">Каталог · {len(cards_data)} карт</span>
    <h1>Карты и цены</h1>
    <p class="lead">Visa и Mastercard банков Казахстана, Кыргызстана, Армении, Турции и других стран.
    Цены — от {fmt_price(min_price)} ₽. Условия указаны по данным партнёров и уточняются при оформлении.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="#catalog">Смотреть каталог</a>
      <a class="btn btn-ghost" href="order.html">Оформить заявку</a>
    </div>
  </div>
</section>

{infographic_cards(cards_data)}

<section id="catalog" class="offers-section">
  <div class="container">
    <div class="section-head"><h2>Все карты</h2>
      <p class="muted">Отфильтруйте по задаче. Цена — за оформление; активация и обслуживание указаны отдельно.</p></div>
    <div class="filter-bar">{chips}</div>
    <div class="offers-grid">{grid}</div>
    <p class="muted small price-note">⚠️ Цены, лимиты и условия приведены по данным партнёров и могут
    меняться. Актуальные тарифы и доступность карты подтверждаются при оформлении заявки.
    Рассрочка — от 990 ₽/мес.</p>
  </div>
</section>

{cta_form_section("", heading="Поможем выбрать карту", sub="Не уверены, что подойдёт? Оставьте заявку — подскажем оптимальный вариант под вашу задачу и бюджет.")}

{faq_block(heading="Вопросы про карты и оформление")}
"""
    return page_shell(f"Карты и цены — {SITE_NAME}",
                      "Каталог зарубежных карт для россиян 2026: Visa и Mastercard, цены и условия.",
                      body, active="cards")


def build_services():
    use_blocks = "".join(
        f"""<div class="use-card">
        <h3>{html.escape(v)}</h3>
        <p>{html.escape(d)}</p>
        <a href="cards.html">Подобрать карту →</a>
      </div>""" for v, d in [
            (USE_CASES["subscribe"], "Оплата Apple, Google, Steam, Netflix, ИИ-сервисов и других подписок, которые не принимают карты РФ."),
            (USE_CASES["travel"], "Оплата отелей, кафе и аренды авто за границей, снятие наличных и выгодная конвертация."),
            (USE_CASES["swift"], "Карты со счётом и возможностью исходящих SWIFT-переводов для крупных операций."),
            (USE_CASES["freelance"], "Приём оплаты от иностранных заказчиков и работа с платёжными системами."),
        ]
    )
    body = f"""
<section class="hero hero-sm">
  <div class="container">
    <span class="eyebrow">Услуги</span>
    <h1>Оформление зарубежных карт под ключ</h1>
    <p class="lead">Берём на себя подбор, оформление в банке и доставку. Вы получаете готовую к работе карту —
    удалённо и с гарантией возврата при отказе банка.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="order.html">Оставить заявку</a>
      <a class="btn btn-ghost" href="cards.html">Каталог карт</a>
    </div>
  </div>
</section>

<section class="trust-band">
  <div class="container trust-inner">
    <div class="trust-item"><b>Удалённо</b><span>без поездок</span></div>
    <div class="trust-item"><b>Гарантия возврата</b><span>при отказе банка</span></div>
    <div class="trust-item"><b>Рассрочка</b><span>от 990 ₽/мес</span></div>
    <div class="trust-item"><b>Сопровождение</b><span>на каждом шаге</span></div>
  </div>
</section>

{steps_block()}

<section class="usecases-section">
  <div class="container">
    <div class="section-head"><h2>Для каких задач</h2>
      <p class="muted">Подбираем карту под конкретную цель.</p></div>
    <div class="use-grid">{use_blocks}</div>
  </div>
</section>

<section class="why-section">
  <div class="container two-col">
    <div class="why-text prose">
      <h2>Почему оформляют через нас</h2>
      <ul>
        <li><strong>Экономия времени.</strong> Не нужно разбираться в требованиях банков и ехать в другую страну.</li>
        <li><strong>Прозрачные цены.</strong> Стоимость карты, активация и обслуживание известны заранее.</li>
        <li><strong>Поддержка в мессенджерах.</strong> Telegram и WhatsApp — отвечаем на вопросы до и после оформления.</li>
        <li><strong>Гибкая доставка.</strong> Виртуальная карта — за день, пластик — курьером или самовывозом.</li>
      </ul>
    </div>
    <div class="why-photos">
      {img_figure("", "support.jpg", "Поддержка клиентов в мессенджерах", cls="flat-img")}
      {img_figure("", "delivery.jpg", "Доставка карты курьером", cls="flat-img")}
    </div>
  </div>
</section>

{cta_form_section("", heading="Оформить карту", sub="Оставьте заявку — перезвоним, подберём карту и рассчитаем стоимость с учётом рассрочки.")}
"""
    return page_shell(f"Услуги — {SITE_NAME}",
                      "Оформление зарубежных карт под ключ: подбор, оформление в банке и доставка.",
                      body, active="services")


def build_order():
    contacts = f"""
    <div class="contact-list">
      <a class="contact-row" href="{CONTACTS['phone_href']}"><span>📞</span><div><b>{CONTACTS['phone']}</b><span class="muted small">{CONTACTS['hours']}</span></div></a>
      <a class="contact-row" href="mailto:{CONTACTS['email']}"><span>✉️</span><div><b>{CONTACTS['email']}</b><span class="muted small">Почта</span></div></a>
      <a class="contact-row" href="{CONTACTS['telegram']}" rel="noopener"><span>✈️</span><div><b>Telegram</b><span class="muted small">Быстрый ответ</span></div></a>
      <a class="contact-row" href="{CONTACTS['whatsapp']}" rel="noopener"><span>💬</span><div><b>WhatsApp</b><span class="muted small">Напишите нам</span></div></a>
    </div>"""
    body = f"""
<section class="order-hero">
  <div class="container two-col order-top">
    <div class="order-intro">
      <span class="eyebrow">Заявка онлайн</span>
      <h1>Оформить зарубежную карту</h1>
      <p class="lead">Заполните форму — перезвоним, подберём карту под задачу и сопроводим оформление.
      Это ни к чему не обязывает.</p>
      <ul class="cta-points">
        <li>Ответим в течение рабочего дня</li>
        <li>Поможем выбрать страну и тип карты</li>
        <li>Рассрочка от 990 ₽/мес и гарантия возврата</li>
      </ul>
      {contacts}
    </div>
    <div class="order-form-wrap">
      <h2 class="order-form-title">Заявка на карту</h2>
      {lead_form("", button="Отправить заявку")}
    </div>
  </div>
</section>

{steps_block()}

{guarantees_block()}

{faq_block(heading="Вопросы перед заявкой")}
"""
    return page_shell(f"Оформить заявку — {SITE_NAME}",
                      "Оставьте заявку на оформление зарубежной карты: подбор, оформление и доставка.",
                      body, active="order")


def _solution_cards(cards_data, *, country=None, use=None, limit=6):
    """Подборка офферов под лендинг (по стране или сценарию)."""
    res = []
    for c in cards_data:
        if country and c.get("country") != country:
            continue
        if use and use not in c.get("useCases", []):
            continue
        res.append(c)
    res.sort(key=lambda c: (not c.get("available", True), c.get("price", 0)))
    return res[:limit]


SUB_FAQ = [
    ("Какие подписки можно оплачивать зарубежной картой?",
     "Apple (App Store, iCloud), Google Play, Steam, PlayStation, Xbox, Netflix, Spotify, "
     "YouTube Premium, ChatGPT/OpenAI, Midjourney, Adobe и большинство других зарубежных сервисов."),
    ("Какая карта лучше для оплаты подписок?",
     "Чаще всего подходят карты Казахстана и Кыргызстана, а также виртуальные карты США/Гонконга. "
     "Подберём вариант под конкретные сервисы, которыми вы пользуетесь."),
    ("Подписка точно спишется без отказа?",
     "Мы подбираем карты, которые стабильно проходят в зарубежных сервисах. Если для сервиса важен "
     "регион — подскажем подходящую страну выпуска карты."),
    ("Нужен ли иностранный номер телефона или адрес?",
     "Для большинства подписок достаточно карты. Если сервис требует регион — поможем настроить "
     "аккаунт. Расскажем все нюансы при оформлении."),
    ("Сколько стоит и как быстро?",
     "Виртуальную карту для подписок можно получить за 1 день, цена — от минимальной в каталоге. "
     "Доступна рассрочка от 990 ₽/мес."),
]


def build_subscriptions(cards_data):
    picks = _solution_cards(cards_data, use="subscribe", limit=6) or _solution_cards(cards_data, limit=6)
    grid = "\n".join(offer_card("", c) for c in picks)
    services = [
        ("play", "Стриминг", "Netflix, Spotify, YouTube Premium, Disney+, Apple Music"),
        ("card", "Магазины приложений", "App Store, Google Play, iCloud, подписки в приложениях"),
        ("bolt", "Игры", "Steam, PlayStation Store, Xbox, Epic Games, Nintendo"),
        ("globe", "ИИ и сервисы", "ChatGPT/OpenAI, Midjourney, Claude, Adobe, Canva"),
    ]
    svc = "".join(
        f"""<div class="use-card"><span class="info-ic">{icon(ic,24)}</span>
        <h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></div>""" for ic, t, d in services
    )
    body = f"""
<section class="hero hero-sm">
  <div class="container">
    <span class="eyebrow">{icon("play",16)} Оплата подписок</span>
    <h1>Карта для оплаты зарубежных подписок</h1>
    <p class="lead">Оформим карту, которой стабильно оплачиваются Apple, Google, Steam, Netflix,
    Spotify и ChatGPT. Удалённо, от 1 дня, с гарантией возврата при отказе банка.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="order.html">Оформить карту</a>
      {tg_button("", label="Спросить в Telegram", cls="btn btn-tg")}
    </div>
  </div>
</section>

<section class="usecases-section">
  <div class="container">
    <div class="section-head"><h2>Что можно оплачивать</h2>
      <p class="muted">Карта работает в большинстве зарубежных сервисов по подписке.</p></div>
    <div class="use-grid">{svc}</div>
  </div>
</section>

<section class="offers-section">
  <div class="container">
    <div class="section-head section-head-row">
      <div><h2>Карты для подписок</h2><p class="muted">Лучшие варианты под онлайн-оплату.</p></div>
      <a class="btn btn-ghost btn-sm" href="cards.html">Весь каталог →</a>
    </div>
    <div class="offers-grid">{grid}</div>
  </div>
</section>

{steps_block()}

{guarantees_block()}

{cta_form_section("", heading="Подберём карту под ваши подписки", sub="Напишите, какими сервисами пользуетесь — подскажем оптимальную карту и оформим.")}

{faq_block(items=SUB_FAQ, heading="Вопросы про оплату подписок")}
"""
    return page_shell(
        f"Карта для оплаты подписок (Apple, Google, Steam, ChatGPT) — {SITE_NAME}",
        "Зарубежная карта для оплаты подписок: Apple, Google Play, Steam, Netflix, Spotify, "
        "ChatGPT. Оформление удалённо за 1 день, с гарантией. Цены и заявка онлайн.",
        body, active="subscriptions")


KZ_FAQ = [
    ("Чем хороша карта банка Казахстана для россиян?",
     "Казахстан рядом, карты Visa и Mastercard local-банков широко принимаются за рубежом и в "
     "онлайне, а оформление часто возможно удалённо. Это один из самых популярных вариантов в 2026."),
    ("Нужно ли ехать в Казахстан?",
     "Часть карт оформляется удалённо. Для некоторых банков нужна разовая поездка или ИИН — "
     "подскажем актуальный порядок и поможем со всеми документами."),
    ("Что такое ИИН и нужен ли он?",
     "ИИН — индивидуальный идентификационный номер (аналог ИНН). Для ряда банков он нужен; "
     "поможем разобраться с получением и оформлением."),
    ("Можно ли оплачивать подписки и путешествия?",
     "Да. Карты Казахстана подходят и для подписок (Apple, Google, Steam), и для оплаты за границей, "
     "и для онлайн-покупок."),
    ("Сколько стоит и как быстро оформляется?",
     "Стоимость — от минимальной в каталоге, сроки зависят от банка и типа карты. Виртуальную можно "
     "получить быстрее, пластик — с доставкой. Доступна рассрочка."),
]


def build_kazakhstan(cards_data):
    picks = _solution_cards(cards_data, country="Казахстан", limit=6) or _solution_cards(cards_data, limit=6)
    grid = "\n".join(offer_card("", c) for c in picks)
    body = f"""
<section class="hero hero-sm">
  <div class="container">
    <span class="eyebrow">🇰🇿 Казахстан</span>
    <h1>Карта банка Казахстана для россиян в 2026</h1>
    <p class="lead">Поможем оформить карту казахстанского банка — Visa и Mastercard для оплаты
    за границей, подписок и онлайн-покупок. Удалённо или с сопровождением поездки, с гарантией.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="order.html">Оформить карту Казахстана</a>
      {tg_button("", label="Спросить в Telegram", cls="btn btn-tg")}
    </div>
  </div>
</section>

{infographic_cards(cards_data)}

<section class="offers-section">
  <div class="container">
    <div class="section-head section-head-row">
      <div><h2>Карты Казахстана</h2><p class="muted">Варианты, которые оформляем чаще всего.</p></div>
      <a class="btn btn-ghost btn-sm" href="cards.html">Весь каталог →</a>
    </div>
    <div class="offers-grid">{grid}</div>
  </div>
</section>

{steps_block()}

{guarantees_block()}

{cta_form_section("", heading="Оформить карту Казахстана", sub="Оставьте заявку — подберём банк, подскажем по ИИН и документам, сопроводим оформление.")}

{faq_block(items=KZ_FAQ, heading="Вопросы про карту Казахстана")}
"""
    return page_shell(
        f"Карта Казахстана для россиян 2026 — оформление удалённо — {SITE_NAME}",
        "Карта банка Казахстана для россиян в 2026: Visa и Mastercard, оформление удалённо или с "
        "сопровождением, помощь с ИИН. Цены, условия и заявка онлайн.",
        body, active="kazakhstan")


def build_kyrgyzstan(cards_data):
    picks = _solution_cards(cards_data, country="Кыргызстан", limit=6) or _solution_cards(cards_data, limit=6)
    grid = "\n".join(offer_card("", c) for c in picks)
    body = f"""
<section class="hero hero-sm">
  <div class="container">
    <span class="eyebrow"><img src="https://flagcdn.com/kg.svg" alt="" width="20" style="border-radius:3px;margin-right:8px"> Кыргызстан</span>
    <h1>Карта банка Кыргызстана для россиян в 2026</h1>
    <p class="lead">Кыргызстан — один из самых выгодных вариантов зарубежной карты: дебетовые и кредитные
    Visa уровня Gold, Platinum и Infinite, мультивалютные счета в долларах и евро, годовое обслуживание
    от $20. Всё оформляется без поездки в Бишкек — дистанционно и с гарантией результата.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="order.html">Оформить карту Кыргызстана</a>
      <a class="btn btn-ghost" href="cards.html">Все карты</a>
    </div>
  </div>
</section>

{infographic_cards(cards_data)}

<section class="offers-section">
  <div class="container">
    <div class="section-head section-head-row">
      <div><h2>Карты Кыргызстана</h2><p class="muted">Варианты, которые оформляем чаще всего.</p></div>
      <a class="btn btn-ghost btn-sm" href="cards.html">Весь каталог →</a>
    </div>
    <div class="offers-grid">{grid}</div>
  </div>
</section>

{steps_block()}

{guarantees_block()}

{cta_form_section("", heading="Оформить карту Кыргызстана", sub="Оставьте заявку — подберём банк и карту, сопроводим оформление удалённо.")}

{faq_block(heading="Вопросы про карту Кыргызстана")}
"""
    return page_shell(
        f"Карта Кыргызстана для россиян 2026 — оформление удалённо — {SITE_NAME}",
        "Карта банка Кыргызстана для россиян в 2026: Visa Gold, Infinite, Platinum — дебетовые и "
        "кредитные, мультивалютные счета USD/EUR. Оформление удалённо, цены от 32 990 ₽, гарантия.",
        body, active="")


def build_tajikistan(cards_data):
    picks = _solution_cards(cards_data, country="Таджикистан", limit=6) or _solution_cards(cards_data, limit=6)
    grid = "\n".join(offer_card("", c) for c in picks)
    body = f"""
<section class="hero hero-sm">
  <div class="container">
    <span class="eyebrow"><img src="https://flagcdn.com/tj.svg" alt="" width="20" style="border-radius:3px;margin-right:8px"> Таджикистан</span>
    <h1>Карта банка Таджикистана для россиян в 2026</h1>
    <p class="lead">Visa Gold таджикского банка — самый быстрый и доступный способ получить рабочую
    зарубежную карту: выпуск всего за 3 дня, долларовый счёт и главное преимущество — карта напрямую
    пополняется переводами из крупных российских банков. Оформляем удалённо, без поездки в Душанбе.</p>
    <div class="hero-actions">
      <a class="btn btn-primary" href="order.html">Оформить карту Таджикистана</a>
      <a class="btn btn-ghost" href="cards.html">Все карты</a>
    </div>
  </div>
</section>

{infographic_cards(cards_data)}

<section class="offers-section">
  <div class="container">
    <div class="section-head section-head-row">
      <div><h2>Карты Таджикистана</h2><p class="muted">Варианты, которые оформляем чаще всего.</p></div>
      <a class="btn btn-ghost btn-sm" href="cards.html">Весь каталог →</a>
    </div>
    <div class="offers-grid">{grid}</div>
  </div>
</section>

{steps_block()}

{guarantees_block()}

{cta_form_section("", heading="Оформить карту Таджикистана", sub="Оставьте заявку — поможем с выпуском и пополнением карты из российских банков.")}

{faq_block(heading="Вопросы про карту Таджикистана")}
"""
    return page_shell(
        f"Карта Таджикистана для россиян 2026 — оформление удалённо — {SITE_NAME}",
        "Карта банка Таджикистана для россиян в 2026: Visa Gold с выпуском за 3 дня, счёт в долларах и "
        "пополнением из российских банков (ВТБ, Сбер, Т-Банк). Оформление удалённо от 21 990 ₽.",
        body, active="")


# ---------------------------------------------------------------------------
# Сборка
# ---------------------------------------------------------------------------

def load_articles():
    items = []
    for f in sorted(ARTICLES_DIR.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            items.append(json.load(fh))
    # порядок: Обзор, Сравнение, Гайд, потом прочее
    order = {"Обзор": 0, "Сравнение": 1, "Гайд": 2}
    items.sort(key=lambda a: order.get(a.get("category", ""), 9))
    return items


def load_offers():
    if not OFFERS_FILE.exists():
        return []
    data = json.load(open(OFFERS_FILE, encoding="utf-8"))
    cards = data.get("cards", [])
    # сортировка: доступные сначала, внутри — по цене
    cards.sort(key=lambda c: (not c.get("available", True), c.get("price", 0)))
    return cards


def main():
    articles = load_articles()
    if not articles:
        print("! Нет статей в", ARTICLES_DIR)
    cards_data = load_offers()
    if not cards_data:
        print("! Нет карт/офферов в", OFFERS_FILE)
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "blog").mkdir(parents=True, exist_ok=True)

    # статические ассеты
    shutil.copyfile(ASSETS_DIR / "styles.css", DIST / "styles.css")
    shutil.copyfile(ASSETS_DIR / "favicon.svg", DIST / "favicon.svg")
    img_src = ASSETS_DIR / "img"
    if img_src.is_dir():
        shutil.copytree(img_src, DIST / "assets" / "img")
    # site.js — общие интерактивные улучшения (флип карточек каталога, оглавление статей)
    if (ASSETS_DIR / "site.js").exists():
        shutil.copyfile(ASSETS_DIR / "site.js", DIST / "site.js")
    # Статические страницы (Mastercard/Visa/UnionPay) + robots/sitemap.
    # В HTML подставляем токен Telegram при сборке (в исходниках — плейсхолдеры).
    static_dir = ROOT / "static"
    if static_dir.is_dir():
        for f in sorted(static_dir.glob("*")):
            if not f.is_file():
                continue
            if f.suffix == ".html":
                txt = (f.read_text(encoding="utf-8")
                       .replace("__TG_TOKEN__", TELEGRAM_BOT_TOKEN)
                       .replace("__TG_CHAT__", TELEGRAM_CHAT_ID))
                (DIST / f.name).write_text(txt, encoding="utf-8")
            else:
                shutil.copyfile(f, DIST / f.name)

    (DIST / "index.html").write_text(build_index(articles, cards_data), encoding="utf-8")
    (DIST / "cards.html").write_text(build_cards(cards_data), encoding="utf-8")
    (DIST / "services.html").write_text(build_services(), encoding="utf-8")
    (DIST / "subscriptions.html").write_text(build_subscriptions(cards_data), encoding="utf-8")
    (DIST / "kazakhstan.html").write_text(build_kazakhstan(cards_data), encoding="utf-8")
    (DIST / "kyrgyzstan.html").write_text(build_kyrgyzstan(cards_data), encoding="utf-8")
    (DIST / "tajikistan.html").write_text(build_tajikistan(cards_data), encoding="utf-8")
    (DIST / "order.html").write_text(build_order(), encoding="utf-8")
    (DIST / "about.html").write_text(build_about(), encoding="utf-8")
    for a in articles:
        (DIST / "blog" / f"{a['slug']}.html").write_text(
            build_article(a, articles), encoding="utf-8")

    print(f"✓ Собрано: {len(articles)} статей, {len(cards_data)} карт -> {DIST}")
    for a in articles:
        print(f"   • [{a.get('category','')}] {a['title']}  (blog/{a['slug']}.html)")


if __name__ == "__main__":
    main()
