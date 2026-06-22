/**
 * Command palette — global search triggered by Cmd/Ctrl+K or a [data-cmd-palette]
 * button. Searches skill titles, descriptions, and glossary terms entirely
 * client-side from window.SKILLS and window.GLOSSARY (data.js). No network,
 * no dependencies.
 *
 * Ported from the ai-engineering-from-scratch site command palette and adapted
 * to the iii skills catalog.
 *
 * Public API (window.CmdPalette): open(), close().
 */
(function () {
  'use strict';

  var PALETTE_ID = 'cmdPalette';
  var MAX_RESULTS = 12;
  var BODY_ATTR = 'data-palette-open';

  var _index = null;
  var _activeIdx = -1;
  var _isOpen = false;
  var _prevFocus = null;

  function buildIndex() {
    if (_index !== null) return _index;
    _index = [];

    if (typeof SKILLS !== 'undefined' && Array.isArray(SKILLS)) {
      for (var i = 0; i < SKILLS.length; i++) {
        var s = SKILLS[i];
        _index.push({
          kind: 'skill',
          name: s.title || s.name || '',
          slug: s.name || '',
          summary: s.description || '',
          url: s.url || '',
        });
      }
    }

    if (typeof GLOSSARY !== 'undefined' && Array.isArray(GLOSSARY)) {
      for (var k = 0; k < GLOSSARY.length; k++) {
        var g = GLOSSARY[k];
        _index.push({
          kind: 'glossary',
          name: g.term || '',
          summary: g.means || '',
          says: g.says || '',
        });
      }
    }

    return _index;
  }

  function scoreItem(item, q) {
    var name = item.name.toLowerCase();
    var slug = (item.slug || '').toLowerCase();
    var summary = (item.summary || '').toLowerCase();
    var says = (item.says || '').toLowerCase();

    var s = 0;
    if (name === q) return 200;
    if (name.indexOf(q) === 0) s += 100;
    else if (name.indexOf(q) !== -1) s += 70;
    if (slug.indexOf(q) !== -1) s += 40;

    var words = q.split(/\s+/).filter(Boolean);
    if (words.length > 1) {
      var blob = name + ' ' + summary + ' ' + says;
      var allIn = words.every(function (w) { return blob.indexOf(w) !== -1; });
      if (allIn) s += s === 0 ? 40 : 15;
    }

    if (summary.indexOf(q) !== -1) s += 25;
    if (says.indexOf(q) !== -1) s += 20;

    if (s === 0 && words.length === 1) {
      var parts = name.split(/[\s\-–—:,]+/).filter(Boolean);
      for (var i = 0; i < parts.length; i++) {
        if (parts[i].indexOf(q) === 0) { s += 30; break; }
      }
      if (s === 0 && summary.indexOf(q) !== -1) s += 12;
    }
    return s;
  }

  function search(query) {
    var q = query.trim().toLowerCase();
    if (!q) return [];
    var items = buildIndex();
    var results = [];
    for (var i = 0; i < items.length; i++) {
      var sc = scoreItem(items[i], q);
      if (sc > 0) results.push({ item: items[i], s: sc });
    }
    results.sort(function (a, b) { return b.s - a.s; });
    return results.slice(0, MAX_RESULTS).map(function (r) { return r.item; });
  }

  function escHtml(str) {
    var d = document.createElement('div');
    d.textContent = str == null ? '' : String(str);
    return d.innerHTML;
  }

  function highlight(text, query) {
    if (!text) return '';
    if (!query) return escHtml(text);
    var lower = text.toLowerCase();
    var q = query.trim().toLowerCase();
    var idx = lower.indexOf(q);
    var matchLen = q.length;
    if (idx === -1) {
      var words = q.split(/\s+/).filter(Boolean);
      for (var i = 0; i < words.length; i++) {
        idx = lower.indexOf(words[i]);
        if (idx !== -1) { matchLen = words[i].length; break; }
      }
    }
    if (idx === -1) return escHtml(text);
    return (
      escHtml(text.slice(0, idx)) +
      '<mark>' + escHtml(text.slice(idx, idx + matchLen)) + '</mark>' +
      escHtml(text.slice(idx + matchLen))
    );
  }

  function truncate(str, max) {
    if (!str || str.length <= max) return str || '';
    var cut = str.slice(0, max).replace(/\s+\S*$/, '');
    return (cut.length > max * 0.6 ? cut : str.slice(0, max)) + '…';
  }

  function createPaletteDOM() {
    if (document.getElementById(PALETTE_ID)) return;
    var isMac = /Mac|iPhone|iPod|iPad/.test(
      (navigator.userAgentData && navigator.userAgentData.platform) || navigator.platform || ''
    );
    var shortcutLabel = isMac ? '⌘K' : 'Ctrl+K';

    var el = document.createElement('div');
    el.id = PALETTE_ID;
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.setAttribute('aria-label', 'Search skills and glossary');

    el.innerHTML =
      '<div class="cp-backdrop" id="cpBackdrop"></div>' +
      '<div class="cp-panel">' +
        '<div class="cp-search-row">' +
          '<svg class="cp-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none"' +
          ' stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"' +
          ' aria-hidden="true"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65"' +
          ' y2="16.65"/></svg>' +
          '<input class="cp-input" id="cpInput" type="search" placeholder="Search skills and glossary…"' +
          ' autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"' +
          ' aria-label="Search" aria-autocomplete="list" aria-controls="cpResults">' +
          '<kbd class="cp-kbd-esc" id="cpKbdEsc">Esc</kbd>' +
        '</div>' +
        '<ul class="cp-results" id="cpResults" role="listbox" aria-label="Search results"></ul>' +
        '<div class="cp-footer">' +
          '<span class="cp-footer-group"><kbd>↑</kbd><kbd>↓</kbd>' +
          '<span class="cp-footer-label">navigate</span></span>' +
          '<span class="cp-footer-group"><kbd>↵</kbd>' +
          '<span class="cp-footer-label">open</span></span>' +
          '<span class="cp-footer-group"><kbd>Esc</kbd>' +
          '<span class="cp-footer-label">close</span></span>' +
          '<span class="cp-footer-shortcut">' + shortcutLabel + '</span>' +
        '</div>' +
      '</div>';

    document.body.appendChild(el);
    document.getElementById('cpBackdrop').addEventListener('click', close);
    document.getElementById('cpKbdEsc').addEventListener('click', close);
    var inp = document.getElementById('cpInput');
    inp.addEventListener('input', _onInput);
    inp.addEventListener('keydown', _onKeyDown);
  }

  function _palEl() { return document.getElementById(PALETTE_ID); }
  function _inputEl() { return document.getElementById('cpInput'); }
  function _listEl() { return document.getElementById('cpResults'); }

  function open() {
    if (_isOpen) { var i = _inputEl(); if (i) i.focus(); return; }
    _prevFocus = document.activeElement || null;
    _isOpen = true;
    _activeIdx = -1;
    createPaletteDOM();
    document.body.setAttribute(BODY_ATTR, '');
    requestAnimationFrame(function () {
      var pal = _palEl();
      if (pal) pal.classList.add('cp-open');
      requestAnimationFrame(function () {
        var inp = _inputEl();
        if (inp) {
          inp.focus();
          var q = inp.value.trim();
          renderResults(q ? search(q) : []);
        }
      });
    });
  }

  function close() {
    if (!_isOpen) return;
    _isOpen = false;
    _activeIdx = -1;
    var pal = _palEl();
    if (pal) pal.classList.remove('cp-open');
    document.body.removeAttribute(BODY_ATTR);
    try {
      if (_prevFocus && typeof _prevFocus.focus === 'function') _prevFocus.focus();
    } catch (_) { /* removed from DOM */ }
    _prevFocus = null;
  }

  function renderResults(results) {
    var list = _listEl();
    if (!list) return;
    var query = (_inputEl() ? _inputEl().value : '').trim();
    var nSkills = (typeof SKILLS !== 'undefined' && SKILLS.length) || 0;
    var nTerms = (typeof GLOSSARY !== 'undefined' && GLOSSARY.length) || 0;

    if (!query) {
      list.innerHTML =
        '<li class="cp-empty" role="option" aria-disabled="true">Type to search ' +
        nSkills + ' skills and ' + nTerms + ' glossary terms</li>';
      _activeIdx = -1;
      return;
    }
    if (results.length === 0) {
      list.innerHTML =
        '<li class="cp-empty" role="option" aria-disabled="true">No results for <em>' +
        escHtml(query) + '</em></li>';
      _activeIdx = -1;
      return;
    }

    var html = '';
    for (var i = 0; i < results.length; i++) {
      var r = results[i];
      var dest;
      var chip;
      var chipClass = 'cp-item-chip';
      if (r.kind === 'skill') {
        dest = r.slug ? 'index.html#' + encodeURIComponent(r.slug) : (r.url || '#');
        chip = 'Skill';
      } else {
        dest = 'glossary.html?q=' + encodeURIComponent(r.name);
        chip = 'Glossary';
        chipClass += ' cp-item-chip--alt';
      }
      var snippet = r.summary ? truncate(r.summary, 110) : '';
      html +=
        '<li class="cp-item" role="option" aria-selected="false" data-idx="' + i + '"' +
        ' data-href="' + escHtml(dest) + '">' +
          '<div class="cp-item-body">' +
            '<span class="' + chipClass + '">' + escHtml(chip) + '</span>' +
            '<span class="cp-item-name">' + highlight(r.name, query) + '</span>' +
            (snippet ? '<span class="cp-item-summary">' + highlight(snippet, query) + '</span>' : '') +
          '</div>' +
          '<svg class="cp-item-arrow" width="12" height="12" viewBox="0 0 24 24" fill="none"' +
          ' stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"' +
          ' aria-hidden="true"><polyline points="9 18 15 12 9 6"/></svg>' +
        '</li>';
    }
    list.innerHTML = html;
    _activeIdx = -1;
    var items = list.querySelectorAll('.cp-item');
    for (var j = 0; j < items.length; j++) {
      items[j].addEventListener('click', _onItemClick);
      items[j].addEventListener('mousemove', _onItemMouseMove);
    }
  }

  function _onInput(e) { renderResults(search(e.target.value)); _activeIdx = -1; }

  function _onKeyDown(e) {
    var list = _listEl();
    var items = list ? list.querySelectorAll('.cp-item') : [];
    var count = items.length;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        if (!count) return;
        _activeIdx = (_activeIdx + 1) % count;
        _updateActive(items);
        break;
      case 'ArrowUp':
        e.preventDefault();
        if (!count) return;
        _activeIdx = (_activeIdx - 1 + count) % count;
        _updateActive(items);
        break;
      case 'Enter': {
        e.preventDefault();
        var target = _activeIdx >= 0 && items[_activeIdx]
          ? items[_activeIdx]
          : count === 1 ? items[0] : null;
        if (target) _navigate(target);
        break;
      }
      case 'Tab':
        e.preventDefault();
        break;
      case 'Escape':
        e.preventDefault();
        close();
        break;
    }
  }

  function _updateActive(items) {
    for (var i = 0; i < items.length; i++) {
      var active = i === _activeIdx;
      items[i].classList.toggle('cp-item--active', active);
      items[i].setAttribute('aria-selected', active ? 'true' : 'false');
      if (active) items[i].scrollIntoView({ block: 'nearest' });
    }
  }

  function _onItemClick(e) { _navigate(e.currentTarget); }

  function _onItemMouseMove(e) {
    var list = _listEl();
    if (!list) return;
    var idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
    if (idx !== _activeIdx) {
      _activeIdx = idx;
      _updateActive(list.querySelectorAll('.cp-item'));
    }
  }

  function _navigate(item) {
    var href = item.getAttribute('data-href');
    if (!href) return;
    close();
    window.location.href = href;
  }

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      if (_isOpen) { var inp = _inputEl(); if (inp) inp.focus(); }
      else open();
    }
  });

  function _init() {
    var triggers = document.querySelectorAll('[data-cmd-palette]');
    for (var i = 0; i < triggers.length; i++) {
      triggers[i].addEventListener('click', function (e) { e.preventDefault(); open(); });
    }
    buildIndex();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

  window.CmdPalette = { open: open, close: close };
}());
