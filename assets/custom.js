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
