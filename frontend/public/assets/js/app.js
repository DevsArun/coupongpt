/* CouponGPT frontend runtime: API helper, toasts, command palette, charts. */
(function () {
  'use strict';

  const CSRF = window.__CGPT__?.csrf || '';

  // ---- Toasts ----
  function ensureToastRoot() {
    let root = document.getElementById('toast-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'toast-root';
      document.body.appendChild(root);
    }
    return root;
  }
  window.toast = function (message, type = 'info', timeout = 3500) {
    const root = ensureToastRoot();
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.textContent = message;
    root.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transition = 'opacity .3s';
      setTimeout(() => el.remove(), 300);
    }, timeout);
  };

  // ---- API helper (talks to PHP /proxy which attaches the token) ----
  async function api(path, { method = 'GET', body = null, query = null } = {}) {
    let url = '/proxy?path=' + encodeURIComponent(path);
    if (query) {
      for (const [k, v] of Object.entries(query)) {
        if (v !== null && v !== undefined && v !== '') url += '&' + encodeURIComponent(k) + '=' + encodeURIComponent(v);
      }
    }
    const opts = { method, headers: { 'Accept': 'application/json' } };
    if (method !== 'GET' && method !== 'HEAD') {
      opts.headers['Content-Type'] = 'application/json';
      opts.headers['X-CSRF-Token'] = CSRF;
      opts.body = JSON.stringify(Object.assign({ csrf_token: CSRF }, body || {}));
    }
    const res = await fetch(url, opts);
    let json = {};
    try { json = await res.json(); } catch (e) { /* noop */ }
    if (!res.ok) {
      const msg = json?.error?.message || json?.error || json?.detail || 'Request failed';
      throw new Error(typeof msg === 'string' ? msg : 'Request failed');
    }
    return json;
  }
  window.cgptApi = api;

  // ---- Command palette (Ctrl/Cmd+K) ----
  const COMMANDS = window.__CGPT__?.commands || [];
  function buildPalette() {
    if (document.getElementById('cmdk')) return;
    const backdrop = document.createElement('div');
    backdrop.id = 'cmdk-backdrop';
    const panel = document.createElement('div');
    panel.id = 'cmdk';
    panel.className = 'card glass';
    panel.innerHTML = `
      <div class="p-3 border-b border-white/10">
        <input id="cmdk-input" placeholder="Search commands or coupons…  (Esc to close)"
          class="w-full bg-transparent outline-none text-white placeholder:text-slate-500 px-2 py-2" />
      </div>
      <ul id="cmdk-list" class="max-h-80 overflow-auto p-2"></ul>`;
    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

    const input = panel.querySelector('#cmdk-input');
    const list = panel.querySelector('#cmdk-list');

    function renderList(items) {
      list.innerHTML = '';
      items.forEach((c) => {
        const li = document.createElement('li');
        li.className = 'px-3 py-2 rounded-lg hover:bg-white/10 cursor-pointer flex items-center justify-between';
        li.innerHTML = `<span>${c.label}</span><span class="text-xs text-slate-500">${c.hint || ''}</span>`;
        li.onclick = () => { close(); if (c.href) location.href = c.href; };
        list.appendChild(li);
      });
    }
    function filter(q) {
      q = q.toLowerCase().trim();
      const base = COMMANDS.filter((c) => c.label.toLowerCase().includes(q));
      renderList(base);
      if (q.length >= 2) {
        const li = document.createElement('li');
        li.className = 'px-3 py-2 rounded-lg hover:bg-white/10 cursor-pointer text-[var(--accent-2)]';
        li.textContent = 'Search coupons for "' + q + '" →';
        li.onclick = () => { location.href = '/search?q=' + encodeURIComponent(q); };
        list.appendChild(li);
      }
    }
    function open() { backdrop.classList.add('open'); panel.classList.add('open'); input.value=''; filter(''); input.focus(); }
    function close() { backdrop.classList.remove('open'); panel.classList.remove('open'); }
    window.__cmdkOpen = open;

    input.addEventListener('input', () => filter(input.value));
    backdrop.addEventListener('click', close);
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); open(); }
      if (e.key === 'Escape') close();
    });
    filter('');
  }
  document.addEventListener('DOMContentLoaded', buildPalette);

  // ---- Tiny SVG charts (no external lib) ----
  window.sparkline = function (el, values, opts = {}) {
    if (!el || !values.length) return;
    const w = opts.width || el.clientWidth || 300, h = opts.height || 60, pad = 4;
    const max = Math.max(...values, 1), min = Math.min(...values, 0);
    const span = max - min || 1;
    const step = (w - pad * 2) / Math.max(values.length - 1, 1);
    const pts = values.map((v, i) => [pad + i * step, h - pad - ((v - min) / span) * (h - pad * 2)]);
    const d = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
    const area = d + ` L ${pts[pts.length-1][0].toFixed(1)} ${h-pad} L ${pad} ${h-pad} Z`;
    el.innerHTML = `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}" preserveAspectRatio="none">
      <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#FF7A18" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="#FF7A18" stop-opacity="0"/></linearGradient></defs>
      <path d="${area}" fill="url(#sg)"/>
      <path d="${d}" fill="none" stroke="#FF9D4D" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
  };

  window.barchart = function (el, labels, values) {
    if (!el) return;
    const max = Math.max(...values, 1);
    el.innerHTML = '<div class="flex items-end gap-1 h-32">' + values.map((v, i) =>
      `<div class="flex-1 flex flex-col items-center justify-end" title="${labels[i]}: ${v}">
         <div data-bar style="height:${(v / max * 100).toFixed(0)}%" class="w-full rounded-t"></div>
       </div>`).join('') + '</div>';
    el.querySelectorAll('[data-bar]').forEach((b) => {
      b.style.background = 'linear-gradient(180deg,#FF9D4D,#FF7A18)';
      b.style.minHeight = '3px';
    });
  };

  // ---- Coupon interactions ----
  window.cgptReveal = function (btn, uuid) {
    const code = btn.getAttribute('data-code') || '';
    if (navigator.clipboard) navigator.clipboard.writeText(code);
    btn.textContent = code + '  ·  copy & open';
    btn.dataset.revealed = '1';
    window.toast('Code copied — opening store…', 'success');
    window.open('/out/' + encodeURIComponent(uuid), '_blank');
  };

  window.cgptFeedback = async function (uuid, worked) {
    try {
      const fd = new FormData();
      fd.append('csrf_token', CSRF);
      fd.append('uuid', uuid);
      fd.append('worked', worked ? '1' : '0');
      await fetch('/fb', { method: 'POST', body: fd });
      window.toast(worked ? 'Thanks — glad it worked!' : 'Thanks for the heads up.', 'info');
    } catch (e) {
      window.toast('Could not record feedback.', 'error');
    }
  };
})();
