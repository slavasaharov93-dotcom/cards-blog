/* =====================================================================
 *  CardsAbroad — виджет ИИ-чата (фронтенд)
 *  Один файл: стили + разметка + логика. Подключается на каждой странице
 *  через <script src="custom.js" defer>. Бэкенд — Cloudflare Worker.
 * ===================================================================== */
(function () {
  "use strict";
  if (window.__caChatLoaded) return;        // защита от двойной вставки
  window.__caChatLoaded = true;

  // --- Настройки ---
  var WORKER_URL = "https://cardsabroad-chat.slavasaharov93.workers.dev";
  var PROVIDER   = "anthropic";
  var MODEL      = "claude-haiku-4-5";       // дёшево и быстро
  var MAX_CHARS  = 2000;                     // лимит длины сообщения (как в Worker)
  var MAX_SEND   = 14;                       // сколько последних сообщений слать
  var STORE_KEY  = "ca_chat_history";

  var GREETING = "Здравствуйте! 👋 Я консультант CardsAbroad. Помогу подобрать зарубежную карту под вашу задачу — подписки, путешествия, переводы или фриланс. С чем помочь?";
  var QUICK = [
    "Карта для подписок (Apple, ChatGPT)",
    "Карта для путешествий",
    "Что нужно для оформления?",
  ];

  // --- Стили ---
  var CSS = "\
.caw-btn{position:fixed;right:20px;bottom:20px;width:60px;height:60px;border:none;border-radius:50%;\
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
.caw-panel{position:fixed;right:20px;bottom:92px;width:370px;max-width:calc(100vw - 32px);\
height:560px;max-height:calc(100vh - 120px);background:#fff;border-radius:18px;z-index:2147483000;\
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
.caw-x{background:none;border:none;color:#fff;cursor:pointer;font-size:24px;line-height:1;\
opacity:.85;padding:0 4px}\
.caw-x:hover{opacity:1}\
.caw-body{flex:1;overflow-y:auto;padding:16px;background:#f7f8fb;display:flex;flex-direction:column;gap:10px}\
.caw-msg{max-width:82%;padding:10px 13px;border-radius:14px;font-size:14px;line-height:1.45;\
word-wrap:break-word;white-space:pre-wrap}\
.caw-bot{align-self:flex-start;background:#fff;color:#1e293b;border:1px solid #e8ebf1;border-bottom-left-radius:4px}\
.caw-user{align-self:flex-end;background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;border-bottom-right-radius:4px}\
.caw-err{align-self:flex-start;background:#fef2f2;color:#b91c1c;border:1px solid #fecaca;font-size:13px}\
.caw-quick{display:flex;flex-wrap:wrap;gap:8px;margin-top:2px}\
.caw-chip{background:#fff;border:1px solid #c7d2fe;color:#4f46e5;border-radius:20px;padding:7px 12px;\
font-size:13px;cursor:pointer;transition:background .15s}\
.caw-chip:hover{background:#eef2ff}\
.caw-typing{align-self:flex-start;background:#fff;border:1px solid #e8ebf1;border-radius:14px;\
padding:12px 14px;display:flex;gap:4px}\
.caw-typing i{width:7px;height:7px;background:#94a3b8;border-radius:50%;animation:cawBlink 1.2s infinite}\
.caw-typing i:nth-child(2){animation-delay:.2s}.caw-typing i:nth-child(3){animation-delay:.4s}\
@keyframes cawBlink{0%,60%,100%{opacity:.3}30%{opacity:1}}\
.caw-foot{border-top:1px solid #eef0f4;padding:10px;display:flex;gap:8px;align-items:flex-end;background:#fff}\
.caw-input{flex:1;border:1px solid #d8dde7;border-radius:12px;padding:9px 12px;font-size:14px;\
resize:none;max-height:96px;outline:none;font-family:inherit;line-height:1.4}\
.caw-input:focus{border-color:#4f46e5}\
.caw-send{border:none;background:linear-gradient(135deg,#2563eb,#4f46e5);color:#fff;width:40px;height:40px;\
border-radius:11px;cursor:pointer;flex-shrink:0;display:flex;align-items:center;justify-content:center}\
.caw-send:disabled{opacity:.5;cursor:default}\
.caw-send svg{width:20px;height:20px}\
.caw-note{font-size:11px;color:#94a3b8;text-align:center;padding:0 10px 8px;background:#fff}\
@media(max-width:480px){.caw-panel{right:8px;left:8px;width:auto;bottom:84px;height:calc(100vh - 100px)}\
.caw-btn{right:14px;bottom:14px}}";

  // --- Вставка стилей ---
  var style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);

  // --- Иконки ---
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
      '<div class="caw-htext"><b>Консультант CardsAbroad</b><span>на связи, отвечает ИИ</span></div>' +
      '<button class="caw-x" aria-label="Свернуть чат">&times;</button>' +
    '</div>' +
    '<div class="caw-body" id="caw-body"></div>' +
    '<div class="caw-foot">' +
      '<textarea class="caw-input" id="caw-input" rows="1" placeholder="Напишите сообщение..." maxlength="' + MAX_CHARS + '"></textarea>' +
      '<button class="caw-send" id="caw-send" aria-label="Отправить">' + ICON_SEND + '</button>' +
    '</div>' +
    '<div class="caw-note">Это ИИ-консультант. Цены и условия уточняйте при заказе.</div>';
  document.body.appendChild(panel);

  var body  = panel.querySelector("#caw-body");
  var input = panel.querySelector("#caw-input");
  var send  = panel.querySelector("#caw-send");
  var closeBtn = panel.querySelector(".caw-x");

  // --- История ---
  var history = [];
  try { history = JSON.parse(sessionStorage.getItem(STORE_KEY) || "[]"); } catch (e) { history = []; }
  function saveHistory() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(history.slice(-30))); } catch (e) {}
  }

  // --- Безопасный мини-Markdown для ответов бота (только **жирный**) ---
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function renderMd(text) {
    var safe = escapeHtml(text);
    safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    return safe;
  }

  // --- Рендер сообщения ---
  function addBubble(role, text) {
    var d = document.createElement("div");
    d.className = "caw-msg " + (role === "user" ? "caw-user" : role === "error" ? "caw-err" : "caw-bot");
    if (role === "assistant") d.innerHTML = renderMd(text);
    else d.textContent = text;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }
  function renderHistory() {
    body.innerHTML = "";
    if (history.length === 0) {
      addBubble("assistant", GREETING);
      renderQuick();
    } else {
      history.forEach(function (m) { addBubble(m.role, m.content); });
    }
  }
  function renderQuick() {
    var wrap = document.createElement("div");
    wrap.className = "caw-quick";
    QUICK.forEach(function (q) {
      var c = document.createElement("button");
      c.className = "caw-chip";
      c.textContent = q;
      c.onclick = function () { wrap.remove(); sendMessage(q); };
      wrap.appendChild(c);
    });
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  // --- Индикатор набора ---
  var typingEl = null;
  function showTyping() {
    typingEl = document.createElement("div");
    typingEl.className = "caw-typing";
    typingEl.innerHTML = "<i></i><i></i><i></i>";
    body.appendChild(typingEl);
    body.scrollTop = body.scrollHeight;
  }
  function hideTyping() { if (typingEl) { typingEl.remove(); typingEl = null; } }

  // --- Отправка ---
  var busy = false;
  function sendMessage(text) {
    text = (text || "").trim();
    if (!text || busy) return;
    if (text.length > MAX_CHARS) text = text.slice(0, MAX_CHARS);

    var quick = body.querySelector(".caw-quick");
    if (quick) quick.remove();

    busy = true;
    send.disabled = true;
    addBubble("user", text);
    history.push({ role: "user", content: text });
    saveHistory();
    input.value = "";
    autoGrow();
    showTyping();

    fetch(WORKER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        provider: PROVIDER,
        model: MODEL,
        messages: history.slice(-MAX_SEND).map(function (m) {
          return { role: m.role, content: m.content };
        }),
      }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        hideTyping();
        if (res.ok && res.j && res.j.reply) {
          addBubble("assistant", res.j.reply);
          history.push({ role: "assistant", content: res.j.reply });
          saveHistory();
        } else {
          var msg = (res.j && res.j.error) ? res.j.error : "Не удалось получить ответ. Попробуйте ещё раз.";
          addBubble("error", msg);
        }
      })
      .catch(function () {
        hideTyping();
        addBubble("error", "Нет связи с сервером. Проверьте интернет и попробуйте снова.");
      })
      .finally(function () {
        busy = false;
        send.disabled = false;
        input.focus();
      });
  }

  // --- Автовысота поля ввода ---
  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 96) + "px";
  }

  // --- События ---
  var opened = false;
  function openPanel() {
    panel.classList.add("caw-open");
    btn.classList.remove("caw-pulse");
    if (!opened) { renderHistory(); opened = true; }
    setTimeout(function () { input.focus(); }, 250);
  }
  function closePanel() { panel.classList.remove("caw-open"); }

  btn.onclick = function () {
    if (panel.classList.contains("caw-open")) closePanel(); else openPanel();
  };
  closeBtn.onclick = closePanel;
  send.onclick = function () { sendMessage(input.value); };
  input.addEventListener("input", autoGrow);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input.value); }
  });
})();
