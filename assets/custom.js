/* Кастомный слой CardsAbroad — правки поверх дизайна (переживают обновления). */
(function () {
  'use strict';
  // Выпадающее меню навигации: клик/тач открывает, клик вне — закрывает.
  document.querySelectorAll('.nav-dd-toggle').forEach(function (t) {
    t.addEventListener('click', function (e) {
      e.preventDefault();
      var dd = t.closest('.nav-dd');
      var open = dd.classList.toggle('open');
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.addEventListener('click', function (e) {
    if (!e.target.closest('.nav-dd')) {
      document.querySelectorAll('.nav-dd.open').forEach(function (dd) {
        dd.classList.remove('open');
        var t = dd.querySelector('.nav-dd-toggle');
        if (t) t.setAttribute('aria-expanded', 'false');
      });
    }
  });
})();

/* =====================================================================
 *  CardsAbroad — виджет ИИ-чата (фронтенд) — версия 2
 *  • Посетитель: OpenAI по умолчанию (выбор модели в списке).
 *  • Админ (по паролю): Claude + кнопка «Написать статью» (публикует в блог).
 *  Один файл: стили + разметка + логика. Бэкенд — Cloudflare Worker.
 * ===================================================================== */
(function () {
  "use strict";
  if (window.__caChatLoaded) return;
  window.__caChatLoaded = true;

  // --- Настройки ---
  var WORKER_URL = "https://cardsabroad-chat.slavasaharov93.workers.dev";
  var MAX_CHARS  = 2000;
  var MAX_SEND   = 14;
  var STORE_KEY  = "ca_chat_history";

  // Модели для посетителей (по умолчанию — первая).
  var PUBLIC_MODELS = [
    { v: "openai|gpt-4o-mini",          t: "⚡ OpenAI — быстрый" },
    { v: "openai|gpt-4o",               t: "🧠 OpenAI — умный" },
    { v: "anthropic|claude-haiku-4-5",  t: "⚡ Claude — быстрый" },
  ];
  // Модели в админ-режиме (всегда Claude).
  var ADMIN_MODELS = [
    { v: "anthropic|claude-haiku-4-5",  t: "⚡ Claude Haiku" },
    { v: "anthropic|claude-sonnet-4-6", t: "🎯 Claude Sonnet" },
    { v: "anthropic|claude-opus-4-8",   t: "🧠 Claude Opus" },
  ];

  var GREETING = "Здравствуйте! 👋 Я консультант CardsAbroad. Помогу подобрать зарубежную карту под вашу задачу — подписки, путешествия, переводы или фриланс. С чем помочь?";
  var QUICK = [
    "Карта для подписок (Apple, ChatGPT)",
    "Карта для путешествий",
    "Что нужно для оформления?",
  ];

  // --- Состояние ---
  var providerSel = "openai", modelSel = "gpt-4o-mini";
  var adminMode = false, adminPass = "";

  // --- Стили ---
  var CSS = "\
.caw-btn{position:fixed;left:20px;bottom:20px;width:60px;height:60px;border:none;border-radius:50%;\
background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;cursor:pointer;z-index:2147483000;\
box-shadow:0 8px 24px rgba(37,99,235,.4);display:flex;align-items:center;justify-content:center;\
transition:transform .2s ease,box-shadow .2s ease}\
.caw-btn:hover{transform:scale(1.07);box-shadow:0 10px 28px rgba(37,99,235,.5)}\
.caw-btn svg{width:28px;height:28px}\
.caw-btn .caw-dot{position:absolute;top:6px;right:6px;width:12px;height:12px;background:#10b981;\
border:2px solid #fff;border-radius:50%}\
.caw-pulse::after{content:'';position:absolute;inset:0;border-radius:50%;\
background:rgba(37,99,235,.45);animation:cawPulse 2s infinite;z-index:-1}\
@keyframes cawPulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(1.8);opacity:0}}\
.caw-panel{position:fixed;left:20px;bottom:92px;width:370px;max-width:calc(100vw - 32px);\
height:580px;max-height:calc(100vh - 120px);background:#fff;border-radius:18px;z-index:2147483000;\
box-shadow:0 18px 50px rgba(15,23,42,.28);display:flex;flex-direction:column;overflow:hidden;\
opacity:0;transform:translateY(16px) scale(.98);pointer-events:none;transition:opacity .22s ease,transform .22s ease;\
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif}\
.caw-panel.caw-open{opacity:1;transform:none;pointer-events:auto}\
.caw-head{background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;padding:14px 16px;\
display:flex;align-items:center;gap:10px}\
.caw-ava{width:38px;height:38px;border-radius:50%;background:rgba(255,255,255,.18);\
display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}\
.caw-htext{flex:1;min-width:0}\
.caw-htext b{display:block;font-size:15px;line-height:1.2}\
.caw-htext span{font-size:12px;opacity:.85;display:flex;align-items:center;gap:5px}\
.caw-htext span::before{content:'';width:7px;height:7px;background:#4ade80;border-radius:50%;display:inline-block}\
.caw-badge{font-size:11px;background:#fbbf24;color:#7c2d12;border-radius:6px;padding:1px 6px;font-weight:700;margin-left:6px}\
.caw-x{background:none;border:none;color:#fff;cursor:pointer;font-size:24px;line-height:1;opacity:.85;padding:0 4px}\
.caw-x:hover{opacity:1}\
.caw-lock{background:none;border:none;color:#fff;cursor:pointer;opacity:.8;padding:0 2px;font-size:16px}\
.caw-lock:hover{opacity:1}\
.caw-bar{display:flex;align-items:center;gap:8px;padding:8px 12px;background:#f0f3fa;border-bottom:1px solid #e5e9f2;font-size:12px}\
.caw-bar label{color:#64748b;flex-shrink:0}\
.caw-select{flex:1;border:1px solid #d8dde7;border-radius:8px;padding:5px 8px;font-size:12px;background:#fff;color:#1e293b;cursor:pointer}\
.caw-login{display:none;gap:6px;padding:8px 12px;background:#fff7ed;border-bottom:1px solid #fed7aa}\
.caw-login.caw-show{display:flex}\
.caw-login input{flex:1;border:1px solid #fdba74;border-radius:8px;padding:6px 9px;font-size:13px;outline:none}\
.caw-login button{border:none;background:#f59e0b;color:#fff;border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer}\
.caw-body{flex:1;overflow-y:auto;padding:16px;background:#f7f8fb;display:flex;flex-direction:column;gap:10px}\
.caw-msg{max-width:82%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;word-wrap:break-word;white-space:pre-wrap}\
.caw-bot{align-self:flex-start;background:#fff;color:#1e293b;border:1px solid #e8ebf1;border-bottom-left-radius:4px}\
.caw-user{align-self:flex-end;background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;border-bottom-right-radius:4px}\
.caw-err{align-self:flex-start;background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;font-size:13px}\
.caw-ok{align-self:flex-start;background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;font-size:13px}\
.caw-quick{display:flex;flex-wrap:wrap;gap:8px;margin-top:2px}\
.caw-chip{background:#fff;border:1px solid #c7d2fe;color:#4f46e5;border-radius:20px;padding:7px 12px;font-size:13px;cursor:pointer;transition:background .15s}\
.caw-chip:hover{background:#eef2ff}\
.caw-typing{align-self:flex-start;background:#fff;border:1px solid #e8ebf1;border-radius:14px;padding:12px 14px;display:flex;gap:4px}\
.caw-typing i{width:7px;height:7px;background:#94a3b8;border-radius:50%;animation:cawBlink 1.2s infinite}\
.caw-typing i:nth-child(2){animation-delay:.2s}.caw-typing i:nth-child(3){animation-delay:.4s}\
@keyframes cawBlink{0%,60%,100%{opacity:.3}30%{opacity:1}}\
.caw-art{display:none;gap:6px;padding:8px 10px;background:#eef2ff;border-top:1px solid #e0e7ff}\
.caw-art.caw-show{display:flex}\
.caw-art input{flex:1;border:1px solid #c7d2fe;border-radius:8px;padding:7px 9px;font-size:13px;outline:none}\
.caw-art button{border:none;background:#4f46e5;color:#fff;border-radius:8px;padding:7px 12px;font-size:13px;cursor:pointer}\
.caw-foot{border-top:1px solid #eef0f4;padding:10px;display:flex;gap:8px;align-items:flex-end;background:#fff}\
.caw-input{flex:1;border:1px solid #d8dde7;border-radius:12px;padding:9px 12px;font-size:14px;resize:none;max-height:96px;outline:none;font-family:inherit;line-height:1.4}\
.caw-input:focus{border-color:#4f46e5}\
.caw-send{border:none;background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;width:40px;height:40px;border-radius:11px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center}\
.caw-send:disabled{opacity:.5;cursor:default}\
.caw-send svg{width:20px;height:20px}\
.caw-artbtn{border:none;background:#eef2ff;color:#4f46e5;border-radius:10px;padding:0 12px;height:40px;cursor:pointer;font-size:13px;flex-shrink:0;white-space:nowrap}\
.caw-note{font-size:11px;color:#94a3b8;text-align:center;padding:0 10px 8px;background:#fff}\
@media(max-width:480px){.caw-panel{right:8px;left:8px;width:auto;bottom:84px;height:calc(100vh - 100px)}.caw-btn{left:14px;bottom:14px}}";

  var style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);

  var ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
  var ICON_SEND = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';

  // --- Кнопка ---
  var btn = document.createElement("button");
  btn.className = "caw-btn caw-pulse";
  btn.setAttribute("aria-label", "Открыть чат с консультантом");
  btn.innerHTML = ICON_CHAT + '<span class="caw-dot"></span>';
  document.body.appendChild(btn);

  // --- Панель ---
  var panel = document.createElement("div");
  panel.className = "caw-panel";
  panel.innerHTML =
    '<div class="caw-head">' +
      '<div class="caw-ava">💳</div>' +
      '<div class="caw-htext"><b>Консультант CardsAbroad<span class="caw-badge" id="caw-badge" style="display:none">АДМИН</span></b><span>на связи, отвечает ИИ</span></div>' +
      '<button class="caw-lock" id="caw-lock" title="Админ-вход" aria-label="Админ-вход">🔒</button>' +
      '<button class="caw-x" aria-label="Свернуть чат">&times;</button>' +
    '</div>' +
    '<div class="caw-bar"><label>Модель:</label><select class="caw-select" id="caw-model"></select></div>' +
    '<div class="caw-login" id="caw-login">' +
      '<input type="password" id="caw-pass" placeholder="Пароль администратора" autocomplete="off">' +
      '<button id="caw-login-btn">Войти</button>' +
    '</div>' +
    '<div class="caw-body" id="caw-body"></div>' +
    '<div class="caw-art" id="caw-art">' +
      '<input type="text" id="caw-topic" placeholder="Тема статьи, напр.: Карта для фрилансера" maxlength="300">' +
      '<button id="caw-art-go">Создать</button>' +
    '</div>' +
    '<div class="caw-foot">' +
      '<textarea class="caw-input" id="caw-input" rows="1" placeholder="Напишите сообщение..." maxlength="' + MAX_CHARS + '"></textarea>' +
      '<button class="caw-artbtn" id="caw-artbtn" style="display:none">✍️ Статья</button>' +
      '<button class="caw-send" id="caw-send" aria-label="Отправить">' + ICON_SEND + '</button>' +
    '</div>' +
    '<div class="caw-note">Это ИИ-консультант. Цены и условия уточняйте при заказе.</div>';
  document.body.appendChild(panel);

  var body    = panel.querySelector("#caw-body");
  var input   = panel.querySelector("#caw-input");
  var send    = panel.querySelector("#caw-send");
  var closeBtn= panel.querySelector(".caw-x");
  var select  = panel.querySelector("#caw-model");
  var lockBtn = panel.querySelector("#caw-lock");
  var loginRow= panel.querySelector("#caw-login");
  var passInp = panel.querySelector("#caw-pass");
  var loginBtn= panel.querySelector("#caw-login-btn");
  var badge   = panel.querySelector("#caw-badge");
  var artBtn  = panel.querySelector("#caw-artbtn");
  var artRow  = panel.querySelector("#caw-art");
  var topicInp= panel.querySelector("#caw-topic");
  var artGo   = panel.querySelector("#caw-art-go");

  // --- Заполнение списка моделей ---
  function fillSelect() {
    var list = adminMode ? ADMIN_MODELS : PUBLIC_MODELS;
    select.innerHTML = "";
    list.forEach(function (m) {
      var o = document.createElement("option");
      o.value = m.v; o.textContent = m.t;
      select.appendChild(o);
    });
    applySelect(list[0].v);
  }
  function applySelect(val) {
    select.value = val;
    var parts = val.split("|");
    providerSel = parts[0]; modelSel = parts[1];
  }
  select.addEventListener("change", function () { applySelect(select.value); });
  fillSelect();

  // --- История ---
  var history = [];
  try { history = JSON.parse(sessionStorage.getItem(STORE_KEY) || "[]"); } catch (e) { history = []; }
  function saveHistory() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(history.slice(-30))); } catch (e) {}
  }

  function escapeHtml(s) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function renderMd(text) { return escapeHtml(text).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>"); }

  function addBubble(role, text) {
    var d = document.createElement("div");
    var cls = role === "user" ? "caw-user" : role === "error" ? "caw-err" : role === "ok" ? "caw-ok" : "caw-bot";
    d.className = "caw-msg " + cls;
    if (role === "assistant") d.innerHTML = renderMd(text);
    else d.textContent = text;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }
  function renderHistory() {
    body.innerHTML = "";
    if (history.length === 0) { addBubble("assistant", GREETING); renderQuick(); }
    else history.forEach(function (m) { addBubble(m.role, m.content); });
  }
  function renderQuick() {
    var wrap = document.createElement("div");
    wrap.className = "caw-quick";
    QUICK.forEach(function (q) {
      var c = document.createElement("button");
      c.className = "caw-chip"; c.textContent = q;
      c.onclick = function () { wrap.remove(); sendMessage(q); };
      wrap.appendChild(c);
    });
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  var typingEl = null;
  function showTyping() {
    typingEl = document.createElement("div");
    typingEl.className = "caw-typing";
    typingEl.innerHTML = "<i></i><i></i><i></i>";
    body.appendChild(typingEl);
    body.scrollTop = body.scrollHeight;
  }
  function hideTyping() { if (typingEl) { typingEl.remove(); typingEl = null; } }

  // --- Базовый payload ---
  function basePayload() {
    var p = { provider: providerSel, model: modelSel };
    if (adminMode) { p.mode = "admin"; p.password = adminPass; }
    return p;
  }

  // --- Отправка сообщения ---
  var busy = false;
  function sendMessage(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    if (text.length > MAX_CHARS) text = text.slice(0, MAX_CHARS);
    var quick = body.querySelector(".caw-quick");
    if (quick) quick.remove();

    busy = true; send.disabled = true;
    addBubble("user", text);
    history.push({ role: "user", content: text });
    saveHistory();
    input.value = ""; autoGrow(); showTyping();

    var p = basePayload();
    p.messages = history.slice(-MAX_SEND).map(function (m) { return { role: m.role, content: m.content }; });

    fetch(WORKER_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        hideTyping();
        if (res.ok && res.j && res.j.reply) {
          addBubble("assistant", res.j.reply);
          history.push({ role: "assistant", content: res.j.reply });
          saveHistory();
        } else {
          addBubble("error", (res.j && res.j.error) ? res.j.error : "Не удалось получить ответ. Попробуйте ещё раз.");
        }
      })
      .catch(function () { hideTyping(); addBubble("error", "Нет связи с сервером. Проверьте интернет и попробуйте снова."); })
      .finally(function () { busy = false; send.disabled = false; input.focus(); });
  }

  // --- Админ-вход ---
  lockBtn.onclick = function () {
    if (adminMode) return;
    loginRow.classList.toggle("caw-show");
    if (loginRow.classList.contains("caw-show")) passInp.focus();
  };
  function doLogin() {
    var pass = passInp.value.trim();
    if (!pass) return;
    loginBtn.disabled = true;
    fetch(WORKER_URL, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "verify_admin", mode: "admin", password: pass }) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j && res.j.admin) {
          adminMode = true; adminPass = pass;
          badge.style.display = ""; artBtn.style.display = "";
          loginRow.classList.remove("caw-show"); lockBtn.textContent = "🔓";
          passInp.value = ""; fillSelect();
          addBubble("ok", "Вход выполнен. Админ-режим: отвечает Claude, доступна кнопка «✍️ Статья».");
        } else {
          addBubble("error", (res.j && res.j.error) ? res.j.error : "Неверный пароль.");
        }
      })
      .catch(function () { addBubble("error", "Нет связи с сервером."); })
      .finally(function () { loginBtn.disabled = false; });
  }
  loginBtn.onclick = doLogin;
  passInp.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); doLogin(); } });

  // --- Написать статью (админ) ---
  artBtn.onclick = function () {
    artRow.classList.toggle("caw-show");
    if (artRow.classList.contains("caw-show")) topicInp.focus();
  };
  function doArticle() {
    var topic = topicInp.value.trim();
    if (!topic || busy) return;
    busy = true; artGo.disabled = true;
    artRow.classList.remove("caw-show");
    addBubble("user", "✍️ Написать статью: " + topic);
    topicInp.value = ""; showTyping();

    var p = basePayload();
    p.action = "write_article"; p.topic = topic;

    fetch(WORKER_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p) })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        hideTyping();
        if (res.ok && res.j && res.j.reply) addBubble("ok", res.j.reply);
        else addBubble("error", (res.j && res.j.error) ? res.j.error : "Не удалось создать статью.");
      })
      .catch(function () { hideTyping(); addBubble("error", "Нет связи с сервером."); })
      .finally(function () { busy = false; artGo.disabled = false; });
  }
  artGo.onclick = doArticle;
  topicInp.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); doArticle(); } });

  // --- Ввод ---
  function autoGrow() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 96) + "px"; }

  var opened = false;
  function openPanel() {
    panel.classList.add("caw-open"); btn.classList.remove("caw-pulse");
    if (!opened) { renderHistory(); opened = true; }
    setTimeout(function () { input.focus(); }, 250);
  }
  function closePanel() { panel.classList.remove("caw-open"); }

  btn.onclick = function () { if (panel.classList.contains("caw-open")) closePanel(); else openPanel(); };
  closeBtn.onclick = closePanel;
  send.onclick = function () { sendMessage(input.value); };
  input.addEventListener("input", autoGrow);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });
})();

/* ===== Ниже: fixes.js — правки дизайна по аудиту (отдельный self-contained IIFE) ===== */
/* ════════════════════════════════════════════════════════════════
   CardsAbroad — fixes.js (правки DOM по дизайн-аудиту)
   Подключать ПОСЛЕДНИМ, перед </body>:
   <script src="fixes.js" defer></script>
   Работает на всех страницах, каждая правка обёрнута в try/catch.
   ════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  /* Карта: страна → код флага и страница «Подробнее» */
  var COUNTRIES = {
    'Казахстан':   { flag: 'kz', page: 'kazakhstan.html' },
    'Кыргызстан':  { flag: 'kg', page: 'kyrgyzstan.html' },
    'Таджикистан': { flag: 'tj', page: 'tajikistan.html' },
    'Армения':     { flag: 'am', page: '' },
    'Турция':      { flag: 'tr', page: '' }
  };

  function slugify(s) {
    return (s || '').toLowerCase()
      .replace(/[^a-zа-яё0-9]+/gi, '-')
      .replace(/^-+|-+$/g, '').slice(0, 60);
  }

  ready(function () {

    /* ── 1. ФЛАГИ: эмодзи → SVG (Windows не показывает флаги-эмодзи) ── */
    try {
      document.querySelectorAll('.offer-flag').forEach(function (el) {
        if (el.querySelector('img')) return;
        var card = el.closest('.offer');
        var name = card && card.querySelector('h3') ? card.querySelector('h3').textContent.trim() : '';
        var c = COUNTRIES[name];
        if (!c) return;
        var img = document.createElement('img');
        img.src = 'https://flagcdn.com/' + c.flag + '.svg';
        img.alt = 'Флаг: ' + name;
        img.width = 38; img.loading = 'lazy';
        el.textContent = '';
        el.appendChild(img);
      });
      /* alt для флагов в выпадающем меню */
      document.querySelectorAll('.nav-flag').forEach(function (img) {
        if (!img.alt) img.alt = '';
        img.setAttribute('aria-hidden', 'true');
      });
    } catch (e) {}

    /* ── 2. КАРТОЧКИ: кнопка «Подробнее о карте» + свёртка характеристик ── */
    try {
      document.querySelectorAll('.offer').forEach(function (card) {
        var face = card.querySelector('.offer-back') || card;
        var cta = face.querySelector('.offer-cta');
        var name = face.querySelector('.offer-name');
        var country = face.querySelector('h3');
        var specs = face.querySelector('.offer-specs');
        if (!cta) return;

        /* 2a. «Оформить» → order.html?card=… (предвыбор на странице заказа) */
        var slug = slugify((country ? country.textContent : '') + '-' + (name ? name.textContent : ''));
        if (cta.getAttribute('href') === 'order.html' && slug) {
          cta.setAttribute('href', 'order.html?card=' + encodeURIComponent(slug) +
            '&country=' + encodeURIComponent(country ? country.textContent.trim() : ''));
        }

        /* 2b. Обёртка действий + «Подробнее о карте» */
        var actions = document.createElement('div');
        actions.className = 'offer-actions';
        cta.parentNode.insertBefore(actions, cta);
        actions.appendChild(cta);

        var cInfo = COUNTRIES[country ? country.textContent.trim() : ''];
        if (cInfo && cInfo.page) {
          var more = document.createElement('a');
          more.className = 'offer-more-link';
          more.href = cInfo.page;
          more.textContent = 'Подробнее о карте';
          actions.appendChild(more);
        }

        /* 2c. Свёртка характеристик: показываем 4, остальные — по клику */
        if (specs && specs.children.length > 4) {
          var hidden = specs.children.length - 4;
          var toggle = document.createElement('button');
          toggle.type = 'button';
          toggle.className = 'offer-specs-toggle';
          toggle.textContent = 'Все характеристики (' + specs.children.length + ') ↓';
          toggle.setAttribute('aria-expanded', 'false');
          specs.parentNode.insertBefore(toggle, specs.nextSibling);
          toggle.addEventListener('click', function () {
            var open = card.classList.toggle('specs-open');
            toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            toggle.textContent = open ? 'Свернуть ↑' : 'Все характеристики (' + specs.children.length + ') ↓';
          });
        }
      });
    } catch (e) {}

    /* ── 3. БЕЙДЖИ: «Хит» только на одной карточке, остальным — свои ярлыки ── */
    try {
      var badges = document.querySelectorAll('.offers-grid .offer-back .offer-badge.hot, .offers-grid .offer:not(.flipper) .offer-badge.hot');
      var labels = [
        null,                                  /* первый остаётся «Хит» */
        { cls: 'value',   text: 'Выгодно' },
        { cls: 'value',   text: 'Низкая плата' },
        { cls: 'premium', text: 'Премиум' }
      ];
      badges.forEach(function (b, i) {
        var l = labels[Math.min(i, labels.length - 1)];
        if (i === 0 || !l) return;
        b.classList.remove('hot');
        b.classList.add(l.cls);
        b.textContent = l.text;
      });
    } catch (e) {}

    /* ── 4. HERO: компактный заголовок + строка доверия + якорь CTA ── */
    try {
      var h1 = document.querySelector('.hero h1');
      if (h1 && /Зарубежная карта для россиян/.test(h1.textContent)) {
        h1.innerHTML = 'Зарубежная карта <span class="grad">под ключ</span>';
      }
      var actions = document.querySelector('.hero-actions');
      if (actions && !document.querySelector('.hero-proof')) {
        var proof = document.createElement('p');
        proof.className = 'hero-proof';
        proof.innerHTML = '<span class="star">★</span> <b>4.9 из 5</b> · более <b>1500</b> оформленных карт · возврат денег при отказе банка';
        actions.parentNode.insertBefore(proof, actions.nextSibling);
      }
    } catch (e) {}

    /* ── 5. КВИЗ: состояние выбора для клавиатуры и скринридеров ── */
    try {
      var opts = document.querySelectorAll('.quiz-opt');
      function syncQuiz() {
        opts.forEach(function (o) {
          o.setAttribute('aria-pressed', o.classList.contains('active') ? 'true' : 'false');
        });
      }
      if (opts.length) {
        syncQuiz();
        document.addEventListener('click', function (e) {
          if (e.target.closest && e.target.closest('.quiz-opt')) setTimeout(syncQuiz, 0);
        });
      }
    } catch (e) {}

    /* ── 6. ORDER: предвыбор карты из ?country=… ── */
    try {
      var params = new URLSearchParams(location.search);
      var country = params.get('country');
      if (country) {
        document.querySelectorAll('select[name="card"]').forEach(function (sel) {
          var opt = Array.prototype.find.call(sel.options, function (o) {
            return o.textContent.indexOf(country) !== -1;
          });
          if (opt) sel.value = opt.value || opt.textContent;
        });
      }
    } catch (e) {}

    /* ── 7. ПЕРЕКЛЮЧАТЕЛЬ ТЕМЫ: показываем одну иконку (противоположную) ── */
    try {
      var tt = document.querySelector('.theme-toggle');
      if (tt) {
        var sync = function () {
          var dark = document.documentElement.getAttribute('data-theme') !== 'light';
          var sun = tt.querySelector('.ic-sun'), moon = tt.querySelector('.ic-moon');
          if (sun) sun.style.display = dark ? '' : 'none';
          if (moon) moon.style.display = dark ? 'none' : '';
          tt.setAttribute('aria-label', dark ? 'Включить светлую тему' : 'Включить тёмную тему');
        };
        sync();
        tt.addEventListener('click', function () { setTimeout(sync, 0); });
      }
    } catch (e) {}

    /* ── 8. ВНЕШНИЕ ССЫЛКИ: безопасный rel ── */
    try {
      document.querySelectorAll('a[target="_blank"]').forEach(function (a) {
        var rel = (a.getAttribute('rel') || '').split(/\s+/);
        if (rel.indexOf('noopener') === -1) rel.push('noopener');
        a.setAttribute('rel', rel.join(' ').trim());
      });
    } catch (e) {}

  });
})();
