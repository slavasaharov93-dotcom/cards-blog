/* CardsAbroad — общие интерактивные улучшения (флип-карточки, оглавление статей) */
(function () {
  'use strict';

  /* ---------- Флип-карточки каталога ----------
     Лицевая сторона — «банковская карта» (страна, название, цена),
     оборот — полные характеристики. Клик/Enter переворачивает.   */
  function buildFlip(card) {
    var specs = card.querySelector('.offer-specs');
    var head = card.querySelector('.offer-head');
    var price = card.querySelector('.offer-price');
    if (!specs || !head || !price) return;

    var flag = head.querySelector('.offer-flag');
    var h3 = head.querySelector('h3');
    var sub = head.querySelector('.offer-sub');
    var badge = head.querySelector('.offer-badge');
    var nameEl = card.querySelector('.offer-name');
    var cta = card.querySelector('.offer-cta');

    var back = document.createElement('div');
    back.className = 'offer-face offer-back';
    while (card.firstChild) back.appendChild(card.firstChild);

    var front = document.createElement('div');
    front.className = 'offer-face offer-front';
    front.innerHTML =
      '<div class="offer-front-top">' +
        (flag ? flag.outerHTML : '<span class="offer-flag">◈</span>') +
        (badge ? badge.outerHTML : '') +
      '</div>' +
      '<div class="offer-front-mid">' +
        '<div class="offer-front-country">' + (h3 ? h3.textContent : '') + '</div>' +
        '<div class="offer-front-name">' + (nameEl ? nameEl.textContent : '') +
          (sub ? ' <span class="muted">· ' + sub.textContent + '</span>' : '') + '</div>' +
      '</div>' +
      '<div class="offer-front-bottom">' +
        '<span class="offer-front-price">' + price.textContent + '</span>' +
        '<span class="offer-front-hint">Характеристики ' +
          '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v5h-5"/></svg>' +
        '</span>' +
      '</div>' +
      (cta ? '<a class="btn btn-primary offer-cta" href="' + cta.getAttribute('href') + '">' + cta.textContent + '</a>' : '');

    var rotor = document.createElement('div');
    rotor.className = 'offer-rotor';
    rotor.appendChild(front);
    rotor.appendChild(back);
    card.appendChild(rotor);
    card.classList.add('flipper');
    card.setAttribute('tabindex', '0');
    card.setAttribute('role', 'button');
    card.setAttribute('aria-expanded', 'false');
    card.setAttribute('aria-label', 'Карта: ' + (h3 ? h3.textContent : '') + '. Нажмите, чтобы посмотреть характеристики');

    function toggle() {
      var on = card.classList.toggle('flipped');
      card.setAttribute('aria-expanded', on ? 'true' : 'false');
    }
    card.addEventListener('click', function (e) {
      if (e.target.closest('a, button')) return;
      toggle();
    });
    card.addEventListener('keydown', function (e) {
      if ((e.key === 'Enter' || e.key === ' ') && !e.target.closest('a, button')) {
        e.preventDefault();
        toggle();
      }
    });
  }
  document.querySelectorAll('.offer').forEach(buildFlip);

  /* ---------- Оглавление статей блога ---------- */
  var prose = document.querySelector('.post .prose');
  if (prose) {
    var hs = prose.querySelectorAll('h2');
    if (hs.length >= 3) {
      var items = '', n = 0;
      hs.forEach(function (h) {
        if (!h.id) h.id = 'sec-' + (++n);
        items += '<li><a href="#' + h.id + '">' + h.textContent + '</a></li>';
      });
      var toc = document.createElement('nav');
      toc.className = 'toc';
      toc.setAttribute('aria-label', 'Содержание статьи');
      toc.innerHTML = '<b>Содержание</b><ol>' + items + '</ol>';
      prose.insertBefore(toc, prose.firstChild);
    }
  }
})();
