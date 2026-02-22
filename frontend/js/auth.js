/*!
 * auth.js — SenseLense Employee Auth
 * - Redirects to login.html if not signed in
 * - Injects the "logged in as" widget into every sidebar footer
 */
(function () {
    const raw = localStorage.getItem('sl-user');

    /* ── 1. Guard: redirect to login if not authed ────────────── */
    if (!raw) {
        window.location.replace('login.html');
        return; // stop all further execution on this page
    }

    const user = JSON.parse(raw);

    /* ── 2. Inject CSS for the user widget ─────────────────────── */
    const style = document.createElement('style');
    style.textContent = `
    .sl-user-widget {
      display: flex; align-items: center; gap: 10px;
      padding: 10px 10px;
      border-radius: var(--radius-sm, 8px);
      margin-top: 10px;
      background: rgba(255,255,255,.03);
      border: 1px solid rgba(255,255,255,.06);
      position: relative;
      transition: background .2s ease;
      cursor: default;
    }
    .sl-user-widget:hover { background: rgba(255,255,255,.06); }

    .sl-user-avatar {
      width: 32px; height: 32px; border-radius: 50%; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      font-size: 12px; font-weight: 800; color: #fff;
      overflow: hidden;
      border: 1.5px solid rgba(255,255,255,.15);
    }
    .sl-user-avatar img {
      width: 100%; height: 100%; object-fit: cover;
    }

    .sl-user-info { flex: 1; min-width: 0; }
    .sl-user-name {
      font-size: 12px; font-weight: 700;
      color: var(--text-primary, #f2f2f2);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .sl-user-role {
      font-size: 10.5px;
      color: var(--text-muted, #666);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      margin-top: 1px;
    }

    .sl-logout-btn {
      background: none; border: none; cursor: pointer;
      color: var(--text-muted, #555);
      padding: 4px; border-radius: 4px;
      display: flex; align-items: center; justify-content: center;
      transition: color .2s ease, background .2s ease;
      flex-shrink: 0;
    }
    .sl-logout-btn:hover { color: var(--negative, #ef4444); background: rgba(239,68,68,.1); }

    /* Tooltip on hover */
    .sl-logout-btn::after {
      content: 'Sign out';
      position: absolute; right: 0; bottom: calc(100% + 6px);
      background: var(--surface-4, #333);
      color: var(--text-primary, #f2f2f2);
      font-size: 11px; padding: 4px 8px; border-radius: 4px;
      white-space: nowrap; pointer-events: none;
      opacity: 0; transition: opacity .15s ease;
    }
    .sl-logout-btn:hover::after { opacity: 1; }
  `;
    document.head.appendChild(style);

    /* ── 3. Inject the user widget once DOM is ready ────────────── */
    function injectWidget() {
        const footer = document.querySelector('.sidebar__footer');
        if (!footer || document.getElementById('sl-user-widget')) return;

        /* Build avatar HTML */
        const avatarHTML = user.avatar
            ? `<img src="${user.avatar}" alt="${user.name}" />`
            : user.initials;

        const avatarStyle = user.avatar
            ? ''
            : `background: linear-gradient(135deg, ${user.color}, color-mix(in srgb, ${user.color} 60%, black));`;

        const widget = document.createElement('div');
        widget.className = 'sl-user-widget';
        widget.id = 'sl-user-widget';
        widget.innerHTML = `
      <div class="sl-user-avatar" style="${avatarStyle}">${avatarHTML}</div>
      <div class="sl-user-info">
        <div class="sl-user-name" title="${user.name}">${user.name}</div>
        <div class="sl-user-role" title="${user.role}">${user.role}</div>
      </div>
      <button class="sl-logout-btn" id="sl-logout-btn" title="Sign out" onclick="SLAuth.logout()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
      </button>`;

        footer.appendChild(widget);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectWidget);
    } else {
        injectWidget();
    }

    /* ── 4. Global API ─────────────────────────────────────────── */
    window.SLAuth = {
        user,
        logout() {
            localStorage.removeItem('sl-user');
            window.location.replace('login.html');
        }
    };
})();
