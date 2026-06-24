/**
 * Skills explorer — theme toggle + catalog/glossary rendering.
 *
 * Reads window.SKILLS and window.GLOSSARY (generated into data.js by
 * skills/site/build.js). Each page calls into the renderers it needs via the
 * data-page attribute on <body>.
 */
(function () {
  'use strict';

  var root = document.documentElement;
  var stored = localStorage.getItem('iii-skills-theme');
  if (stored) {
    root.setAttribute('data-theme', stored);
  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    root.setAttribute('data-theme', 'dark');
  } else {
    root.setAttribute('data-theme', 'light');
  }

  document.addEventListener('DOMContentLoaded', function () {
    initThemeToggle();
    var page = document.body.getAttribute('data-page');
    if (page === 'catalog') renderCatalog();
    if (page === 'glossary') renderGlossary();
  });

  function escHtml(str) {
    var d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
  }

  function updateThemeIcon() {
    var icon = document.getElementById('themeIcon');
    if (!icon) return;
    icon.textContent = root.getAttribute('data-theme') === 'light' ? 'N' : 'D';
  }

  function initThemeToggle() {
    updateThemeIcon();
    var btn = document.getElementById('themeToggle');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      root.setAttribute('data-theme', next);
      localStorage.setItem('iii-skills-theme', next);
      updateThemeIcon();
    });
  }

  // ── Catalog page ───────────────────────────────────────────────────────
  function renderCatalog() {
    var grid = document.getElementById('skillGrid');
    if (!grid || typeof SKILLS === 'undefined') return;

    var count = document.getElementById('skillCount');
    if (count) count.textContent = String(SKILLS.length);

    var html = '';
    for (var i = 0; i < SKILLS.length; i++) {
      var s = SKILLS[i];
      html +=
        '<a class="card" id="' + escHtml(s.name) + '" href="' + escHtml(s.url || '#') + '"' +
        (s.url ? ' target="_blank" rel="noopener"' : '') + '>' +
          '<div class="card-head">' +
            '<span class="card-chip">Skill</span>' +
            '<code class="card-slug">' + escHtml(s.name) + '</code>' +
          '</div>' +
          '<h2 class="card-title">' + escHtml(s.title) + '</h2>' +
          '<p class="card-desc">' + escHtml(s.description) + '</p>' +
        '</a>';
    }
    grid.innerHTML = html;

    // Deep-link: highlight the skill named in the URL hash.
    if (location.hash.length > 1) {
      var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (target) {
        target.classList.add('card--active');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }

  // ── Glossary page ──────────────────────────────────────────────────────
  function renderGlossary() {
    var list = document.getElementById('glossaryList');
    if (!list || typeof GLOSSARY === 'undefined') return;

    var search = document.getElementById('glossarySearch');
    var sorted = GLOSSARY.slice().sort(function (a, b) {
      return a.term.toLowerCase().localeCompare(b.term.toLowerCase());
    });

    function draw(filter) {
      var q = (filter || '').trim().toLowerCase();
      var html = '';
      var shown = 0;
      for (var i = 0; i < sorted.length; i++) {
        var g = sorted[i];
        var blob = (g.term + ' ' + g.means + ' ' + g.says).toLowerCase();
        if (q && blob.indexOf(q) === -1) continue;
        shown++;
        html +=
          '<div class="term">' +
            '<dt class="term-name">' + escHtml(g.term) + '</dt>' +
            '<dd class="term-means">' + escHtml(g.means) + '</dd>' +
          '</div>';
      }
      list.innerHTML = html ||
        '<p class="empty">No glossary terms match <em>' + escHtml(filter) + '</em>.</p>';
      var count = document.getElementById('termCount');
      if (count) count.textContent = String(shown);
    }

    draw('');

    // Pre-populate from ?q= (used by the command palette deep-link).
    var params = new URLSearchParams(location.search);
    var initial = params.get('q') || '';
    if (initial && search) {
      search.value = initial;
      draw(initial);
    }
    if (search) {
      search.addEventListener('input', function (e) { draw(e.target.value); });
    }
  }
}());
