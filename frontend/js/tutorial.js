/*!
 * tutorial.js — SenseLense Animated Onboarding Tutorial
 * Self-contained: injects its own CSS, no external dependencies.
 */
(function () {
  /* ─────────────── CSS ─────────────── */
  const style = document.createElement('style');
  style.textContent = `
    /* ── Tutorial Prompt Modal ───────────────────────────────── */
    #sl-tut-backdrop {
      position: fixed; inset: 0;
      background: rgba(0,0,0,.7);
      backdrop-filter: blur(6px);
      z-index: 99000;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; transition: opacity .35s ease;
    }
    #sl-tut-backdrop.visible { opacity: 1; }

    #sl-tut-prompt {
      background: var(--surface-2, #1a1a1a);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 20px;
      padding: 40px 44px;
      width: 420px; max-width: calc(100vw - 40px);
      text-align: center;
      box-shadow: 0 40px 100px rgba(0,0,0,.6);
      transform: translateY(24px) scale(.96);
      transition: transform .4s cubic-bezier(.34,1.56,.64,1), opacity .35s ease;
      opacity: 0;
    }
    #sl-tut-backdrop.visible #sl-tut-prompt {
      transform: translateY(0) scale(1);
      opacity: 1;
    }
    #sl-tut-prompt .prompt-icon {
      width: 72px; height: 72px;
      background: rgba(204,0,0,.12);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 20px;
      animation: prompt-bounce 2.4s ease-in-out infinite;
    }
    @keyframes prompt-bounce {
      0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)}
    }
    #sl-tut-prompt h2 {
      font-size: 22px; font-weight: 800;
      color: var(--text-primary, #f2f2f2);
      margin-bottom: 10px;
    }
    #sl-tut-prompt p {
      font-size: 14px; line-height: 1.6;
      color: var(--text-muted, #888);
      margin-bottom: 28px;
    }
    .prompt-actions { display: flex; flex-direction: column; gap: 10px; }
    .btn-tut-begin {
      background: var(--red, #CC0000);
      color: #fff; border: none;
      border-radius: 10px; padding: 13px 0;
      font-size: 15px; font-weight: 700;
      cursor: pointer; font-family: inherit;
      transition: all .2s ease;
    }
    .btn-tut-begin:hover { transform: translateY(-2px); filter: brightness(1.15); box-shadow: 0 0 24px rgba(204,0,0,.4); }
    .btn-tut-skip {
      background: transparent;
      color: var(--text-muted, #888);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 10px; padding: 11px 0;
      font-size: 13px; font-weight: 500;
      cursor: pointer; font-family: inherit;
      transition: all .2s ease;
    }
    .btn-tut-skip:hover { color: var(--text-primary, #f2f2f2); border-color: rgba(255,255,255,.25); }

    /* ── Tutorial Overlay ────────────────────────────────────── */
    #sl-tut-overlay {
      position: fixed; inset: 0;
      background: rgba(0,0,0,.82);
      backdrop-filter: blur(8px);
      z-index: 99000;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; transition: opacity .4s ease;
    }
    #sl-tut-overlay.visible { opacity: 1; }

    #sl-tut-card {
      background: var(--surface-2, #1a1a1a);
      border: 1px solid rgba(255,255,255,.1);
      border-radius: 24px;
      width: 540px; max-width: calc(100vw - 32px);
      box-shadow: 0 48px 120px rgba(0,0,0,.7);
      overflow: hidden;
      transform: scale(.92);
      transition: transform .45s cubic-bezier(.34,1.56,.64,1);
    }
    #sl-tut-overlay.visible #sl-tut-card { transform: scale(1); }

    .tut-illustration {
      height: 200px;
      position: relative; overflow: hidden;
      background: linear-gradient(135deg, #0d0d0d, #1a1a1a);
      display: flex; align-items: center; justify-content: center;
    }

    .tut-content { padding: 28px 32px 24px; }
    .tut-step-badge {
      display: inline-block;
      font-size: 11px; font-weight: 700;
      letter-spacing: .1em; text-transform: uppercase;
      color: var(--red, #CC0000);
      background: rgba(204,0,0,.12);
      padding: 4px 10px; border-radius: 99px;
      margin-bottom: 12px;
    }
    .tut-title {
      font-size: 22px; font-weight: 800;
      color: var(--text-primary, #f2f2f2);
      margin-bottom: 10px;
    }
    .tut-desc {
      font-size: 14px; line-height: 1.65;
      color: var(--text-secondary, #9a9a9a);
    }
    .tut-footer {
      display: flex; align-items: center;
      justify-content: space-between;
      padding: 16px 32px 24px;
      border-top: 1px solid rgba(255,255,255,.06);
    }
    .tut-dots { display: flex; gap: 6px; }
    .tut-dot {
      width: 7px; height: 7px;
      border-radius: 99px;
      background: var(--surface-4, #2e2e2e);
      transition: all .3s ease;
      cursor: pointer;
    }
    .tut-dot.active {
      width: 20px;
      background: var(--red, #CC0000);
    }
    .tut-nav { display: flex; gap: 8px; align-items: center; }
    .btn-tut-prev, .btn-tut-next, .btn-tut-done {
      font-family: inherit; cursor: pointer;
      border-radius: 8px; font-weight: 600; font-size: 13px;
      transition: all .2s ease;
    }
    .btn-tut-prev {
      background: transparent;
      border: 1px solid rgba(255,255,255,.12);
      color: var(--text-secondary, #9a9a9a);
      padding: 8px 16px;
    }
    .btn-tut-prev:hover { border-color: rgba(255,255,255,.3); color: var(--text-primary, #f2f2f2); }
    .btn-tut-next, .btn-tut-done {
      background: var(--red, #CC0000);
      border: none; color: #fff;
      padding: 8px 20px;
    }
    .btn-tut-next:hover, .btn-tut-done:hover {
      filter: brightness(1.15);
      transform: translateY(-1px);
      box-shadow: 0 8px 20px rgba(204,0,0,.35);
    }

    /* ── Step slide transition ───────────────────────────────── */
    .tut-anim-out { animation: tut-slide-out .28s ease forwards; }
    .tut-anim-in  { animation: tut-slide-in .35s cubic-bezier(.34,1.56,.64,1) forwards; }
    @keyframes tut-slide-out {
      to { opacity:0; transform: translateX(-32px) scale(.97); }
    }
    @keyframes tut-slide-in {
      from { opacity:0; transform: translateX(32px) scale(.97); }
      to   { opacity:1; transform: translateX(0)   scale(1); }
    }

    /* ═══════════════════ ILLUSTRATIONS ═══════════════════════ */

    /* Step 0 — Welcome */
    .il-welcome { position: relative; width: 100%; height: 100%; }
    .il-welcome .rings span {
      position: absolute; top:50%; left:50%;
      border-radius: 50%;
      border: 1.5px solid rgba(204,0,0,.25);
      transform: translate(-50%,-50%);
      animation: ring-expand 3s ease-out infinite;
    }
    .il-welcome .rings span:nth-child(1){width:60px;height:60px;animation-delay:0s}
    .il-welcome .rings span:nth-child(2){width:100px;height:100px;animation-delay:.5s}
    .il-welcome .rings span:nth-child(3){width:148px;height:148px;animation-delay:1s}
    .il-welcome .rings span:nth-child(4){width:196px;height:196px;animation-delay:1.5s}
    @keyframes ring-expand {
      0%{opacity:.8;transform:translate(-50%,-50%) scale(.7)}
      100%{opacity:0;transform:translate(-50%,-50%) scale(1.4)}
    }
    .il-welcome .center-dot {
      position:absolute; top:50%; left:50%;
      transform:translate(-50%,-50%);
      width:52px; height:52px; border-radius:50%;
      background: radial-gradient(circle, var(--red,#CC0000), #990000);
      box-shadow: 0 0 32px rgba(204,0,0,.5);
      display:flex; align-items:center; justify-content:center;
      animation: dot-pulse 2s ease-in-out infinite;
    }
    @keyframes dot-pulse {
      0%,100%{box-shadow:0 0 24px rgba(204,0,0,.4)}
      50%{box-shadow:0 0 48px rgba(204,0,0,.7)}
    }

    /* Step 1 — Dashboard */
    .il-dashboard { display:flex; gap:10px; align-items:flex-end; padding: 20px 28px 0; width:100%; justify-content:center; }
    .il-bar {
      width:36px; border-radius:6px 6px 0 0;
      background: linear-gradient(to top, var(--red,#CC0000), rgba(204,0,0,.4));
      animation: bar-grow .8s cubic-bezier(.34,1.56,.64,1) both;
      transform-origin: bottom;
    }
    .il-bar:nth-child(1){height:80px;animation-delay:.0s}
    .il-bar:nth-child(2){height:120px;animation-delay:.1s}
    .il-bar:nth-child(3){height:60px;animation-delay:.2s}
    .il-bar:nth-child(4){height:140px;animation-delay:.3s}
    .il-bar:nth-child(5){height:100px;animation-delay:.4s}
    .il-bar:nth-child(6){height:90px;animation-delay:.5s}
    @keyframes bar-grow {
      from{transform:scaleY(0)} to{transform:scaleY(1)}
    }

    /* Step 2 — Clients */
    .il-clients { display:flex; gap:14px; align-items:center; justify-content:center; width:100%; }
    .il-avatar {
      width:52px; height:52px; border-radius:50%;
      background: linear-gradient(135deg, #990000, var(--red,#CC0000));
      display:flex; align-items:center; justify-content:center;
      font-size:18px; font-weight:800; color:#fff;
      animation: avatar-pop .5s cubic-bezier(.34,1.56,.64,1) both;
      box-shadow: 0 0 0 2px rgba(204,0,0,.3);
    }
    .il-avatar:nth-child(1){animation-delay:.0s}
    .il-avatar:nth-child(2){animation-delay:.15s;width:62px;height:62px;font-size:22px}
    .il-avatar:nth-child(3){animation-delay:.3s}
    .il-avatar:nth-child(4){animation-delay:.45s}
    @keyframes avatar-pop {
      from{opacity:0;transform:scale(0) rotate(-15deg)}
      to{opacity:1;transform:scale(1) rotate(0)}
    }
    .il-connector {
      width:24px; height:2px;
      background: linear-gradient(90deg, var(--red,#CC0000), transparent);
      animation: connector-grow .4s ease both;
      animation-delay: .5s;
    }
    @keyframes connector-grow { from{transform:scaleX(0)} to{transform:scaleX(1)} }

    /* Step 3 — Sessions / Timeline */
    .il-timeline { display:flex; flex-direction:column; gap:0; padding: 16px 40px; width:100%; position:relative; }
    .il-timeline::before {
      content:''; position:absolute; left:55px; top:20px; bottom:20px;
      width:2px; background: rgba(255,255,255,.08);
    }
    .il-tl-event {
      display:flex; align-items:center; gap:14px; padding:8px 0;
      animation: tl-fade-in .5s ease both;
    }
    .il-tl-event:nth-child(1){animation-delay:.1s}
    .il-tl-event:nth-child(2){animation-delay:.3s}
    .il-tl-event:nth-child(3){animation-delay:.5s}
    @keyframes tl-fade-in {
      from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)}
    }
    .il-tl-dot {
      width:12px; height:12px; border-radius:50%; flex-shrink:0;
      position:relative; z-index:1;
    }
    .il-tl-dot.red { background:var(--red,#CC0000); box-shadow:0 0 8px rgba(204,0,0,.6); }
    .il-tl-dot.blue { background:#3B82F6; box-shadow:0 0 8px rgba(59,130,246,.5); }
    .il-tl-bar { height:8px; border-radius:4px; flex:1; opacity:.8; }

    /* Step 4 — Recording */
    .il-record { position:relative; display:flex; align-items:center; justify-content:center; width:100%; height:100%; }
    .il-cam-ring {
      width:90px; height:90px; border-radius:50%;
      border: 3px solid var(--red,#CC0000);
      display:flex; align-items:center; justify-content:center;
      animation: cam-pulse 1.8s ease-in-out infinite;
    }
    @keyframes cam-pulse {
      0%,100%{box-shadow:0 0 0 0 rgba(204,0,0,.4),0 0 0 10px rgba(204,0,0,.08)}
      50%{box-shadow:0 0 0 14px rgba(204,0,0,.2),0 0 0 28px rgba(204,0,0,.04)}
    }
    .il-cam-inner {
      width:50px; height:50px; border-radius:50%;
      background: radial-gradient(var(--red,#CC0000), #770000);
      animation: cam-inner-pulse 1.8s ease-in-out infinite;
    }
    @keyframes cam-inner-pulse {
      0%,100%{transform:scale(1)} 50%{transform:scale(1.08)}
    }
    .il-mic-wave {
      position:absolute; right:100px;
      display:flex; gap:4px; align-items:center;
    }
    .il-mic-bar {
      width:4px; border-radius:2px;
      background: #3B82F6;
      animation: mic-wave 1s ease-in-out infinite alternate;
    }
    .il-mic-bar:nth-child(1){height:12px;animation-delay:0s}
    .il-mic-bar:nth-child(2){height:24px;animation-delay:.15s}
    .il-mic-bar:nth-child(3){height:18px;animation-delay:.3s}
    .il-mic-bar:nth-child(4){height:30px;animation-delay:.1s}
    .il-mic-bar:nth-child(5){height:14px;animation-delay:.25s}
    @keyframes mic-wave {
      from{transform:scaleY(1)} to{transform:scaleY(.3)}
    }

    /* Step 5 — Emotions */
    .il-emotions { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; padding:24px; align-items:center; }
    .il-chip {
      padding:8px 16px; border-radius:99px;
      font-size:13px; font-weight:700;
      animation: chip-pop .5s cubic-bezier(.34,1.56,.64,1) both;
    }
    .il-chip.happy { background:rgba(34,197,94,.15); color:#22C55E; animation-delay:.0s; }
    .il-chip.engaged{ background:rgba(59,130,246,.15); color:#60A5FA; animation-delay:.15s; }
    .il-chip.neutral{ background:rgba(234,179,8,.15); color:#EAB308; animation-delay:.3s; }
    .il-chip.confused{ background:rgba(249,115,22,.15); color:#FB923C; animation-delay:.45s; }
    .il-chip.active-chip {
      animation: chip-pulse 1.4s ease-in-out infinite, chip-pop .5s cubic-bezier(.34,1.56,.64,1) both;
      animation-delay: .6s, .6s;
    }
    @keyframes chip-pop {
      from{opacity:0;transform:scale(.5)} to{opacity:1;transform:scale(1)}
    }
    @keyframes chip-pulse {
      0%,100%{transform:scale(1)} 50%{transform:scale(1.08)}
    }

    /* Step 6 — Insights */
    .il-insights { display:flex; flex-direction:column; gap:10px; padding:20px 32px; width:100%; }
    .il-insight-row {
      height:10px; border-radius:5px;
      background: rgba(255,255,255,.06);
      overflow: hidden;
      animation: insight-appear .4s ease both;
    }
    .il-insight-row:nth-child(1){animation-delay:.0s}
    .il-insight-row:nth-child(2){animation-delay:.15s}
    .il-insight-row:nth-child(3){animation-delay:.3s}
    .il-insight-row:nth-child(4){animation-delay:.45s}
    @keyframes insight-appear { from{opacity:0;transform:scaleX(0)} to{opacity:1;transform:scaleX(1)} }
    .il-insight-fill {
      height:100%; border-radius:5px;
      background: linear-gradient(90deg, var(--red,#CC0000), rgba(204,0,0,.4));
      animation: fill-grow 1.2s cubic-bezier(.34,1.56,.64,1) both;
    }
    @keyframes fill-grow { from{width:0} to{width:var(--w,70%)} }

    /* Step 7 — Settings */
    .il-settings { display:flex; align-items:center; justify-content:center; gap:24px; width:100%; height:100%; }
    .il-color-wheel {
      width:80px; height:80px; border-radius:50%;
      background: conic-gradient(red,yellow,lime,cyan,blue,magenta,red);
      animation: wheel-spin 4s linear infinite;
      box-shadow: 0 0 24px rgba(255,255,255,.15);
    }
    @keyframes wheel-spin { to{transform:rotate(360deg)} }
    .il-theme-cards { display:flex; flex-direction:column; gap:8px; }
    .il-theme-card {
      width:100px; height:30px; border-radius:8px;
      animation: card-slide .5s ease both;
    }
    .il-theme-card.dark { background:#111; border:1px solid rgba(255,255,255,.1); animation-delay:.1s; }
    .il-theme-card.light { background:#f0f0f0; border:1px solid rgba(0,0,0,.1); animation-delay:.25s; }
    @keyframes card-slide { from{opacity:0;transform:translateX(16px)} to{opacity:1;transform:translateX(0)} }

    /* Step 8 — Done / Confetti */
    .il-done { position:relative; width:100%; height:100%; overflow:hidden; display:flex; align-items:center; justify-content:center; }
    .il-confetti-piece {
      position:absolute;
      width:8px; height:8px;
      border-radius:2px;
      animation: confetti-fall 2.5s ease-in infinite;
    }
    @keyframes confetti-fall {
      0%{transform:translateY(-20px) rotate(0deg);opacity:1}
      100%{transform:translateY(200px) rotate(720deg);opacity:0}
    }
    .il-done-star {
      font-size:64px;
      animation: star-bounce 1s cubic-bezier(.34,1.56,.64,1) both;
      filter: drop-shadow(0 0 24px rgba(255,200,0,.5));
    }
    @keyframes star-bounce {
      from{transform:scale(0) rotate(-30deg)} to{transform:scale(1) rotate(0)}
    }
  `;
  document.head.appendChild(style);

  /* ─────────────── STEP DATA ─────────────── */
  const STEPS = [
    {
      badge: 'Welcome',
      title: 'Welcome to SenseLense',
      desc: 'SenseLense is your AI-powered sales conversation intelligence platform. It syncs facial emotion data from <strong>Presage</strong> and speech transcriptions from <strong>ElevenLabs</strong> into a unified timeline — giving you real insights after every meeting.',
      illustration: `
        <div class="il-welcome">
          <div class="rings">
            <span></span><span></span><span></span><span></span>
          </div>
          <div class="center-dot">
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
          </div>
        </div>`
    },
    {
      badge: 'Step 1 of 7 — Dashboard',
      title: 'Your Dashboard at a Glance',
      desc: 'The <strong>Dashboard</strong> is your home base. It shows total clients, sessions recorded, average emotional sentiment, and engagement score — all updated in real-time as your session data comes in.',
      illustration: `
        <div class="il-dashboard">
          <div class="il-bar"></div><div class="il-bar"></div><div class="il-bar"></div>
          <div class="il-bar"></div><div class="il-bar"></div><div class="il-bar"></div>
        </div>`
    },
    {
      badge: 'Step 2 of 7 — Clients',
      title: 'Manage Your Contacts',
      desc: 'The <strong>Clients</strong> section stores everyone you sell to. Each client has a profile showing their session history, average sentiment score, and engagement trend over time.',
      illustration: `
        <div class="il-clients">
          <div class="il-avatar">JD</div>
          <div class="il-connector"></div>
          <div class="il-avatar">MK</div>
          <div class="il-connector"></div>
          <div class="il-avatar">AL</div>
          <div class="il-connector"></div>
          <div class="il-avatar">RS</div>
        </div>`
    },
    {
      badge: 'Step 3 of 7 — Sessions',
      title: 'Review Past Sessions',
      desc: 'Every recorded meeting is saved as a <strong>Session</strong>. Click any session to view its full emotional timeline — a chronological log of Presage emotion events and ElevenLabs transcript chunks, synced by millisecond.',
      illustration: `
        <div class="il-timeline">
          <div class="il-tl-event">
            <div class="il-tl-dot red"></div>
            <div class="il-tl-bar" style="background:linear-gradient(90deg,rgba(204,0,0,.5),transparent);width:65%"></div>
          </div>
          <div class="il-tl-event">
            <div class="il-tl-dot blue"></div>
            <div class="il-tl-bar" style="background:linear-gradient(90deg,rgba(59,130,246,.5),transparent);width:80%"></div>
          </div>
          <div class="il-tl-event">
            <div class="il-tl-dot red"></div>
            <div class="il-tl-bar" style="background:linear-gradient(90deg,rgba(204,0,0,.5),transparent);width:50%"></div>
          </div>
        </div>`
    },
    {
      badge: 'Step 4 of 7 — New Session',
      title: 'Start a Recording',
      desc: 'Hit <strong>New Session</strong> to begin capturing. <span style="color:#CC0000">Presage</span> watches the camera and logs facial emotion events. <span style="color:#60A5FA">ElevenLabs</span> transcribes speech in real-time. Both streams are stamped and merged automatically.',
      illustration: `
        <div class="il-record">
          <div class="il-cam-ring"><div class="il-cam-inner"></div></div>
          <div class="il-mic-wave">
            <div class="il-mic-bar"></div><div class="il-mic-bar"></div>
            <div class="il-mic-bar"></div><div class="il-mic-bar"></div>
            <div class="il-mic-bar"></div>
          </div>
        </div>`
    },
    {
      badge: 'Step 5 of 7 — Emotion Tracking',
      title: 'Live Emotion Intelligence',
      desc: 'During a recording, <strong>Presage</strong> samples the camera every 2.4 seconds. Each detected emotion is tagged, timestamped, and stored alongside the transcript. Chips update live so you can follow the meeting\'s mood in the moment.',
      illustration: `
        <div class="il-emotions">
          <div class="il-chip happy">Happy</div>
          <div class="il-chip engaged">Engaged</div>
          <div class="il-chip neutral">Neutral</div>
          <div class="il-chip confused active-chip">Confused</div>
        </div>`
    },
    {
      badge: 'Step 6 of 7 — AI Insights',
      title: 'Actionable Insights After Each Call',
      desc: 'When a session ends, SenseLense calculates <strong>average valence</strong>, <strong>emotion breakdown</strong>, and <strong>engagement score</strong>. The insights endpoint is ready to be wired to an LLM for richer AI-generated coaching notes.',
      illustration: `
        <div class="il-insights">
          <div class="il-insight-row"><div class="il-insight-fill" style="--w:75%"></div></div>
          <div class="il-insight-row"><div class="il-insight-fill" style="--w:55%"></div></div>
          <div class="il-insight-row"><div class="il-insight-fill" style="--w:88%"></div></div>
          <div class="il-insight-row"><div class="il-insight-fill" style="--w:42%"></div></div>
        </div>`
    },
    {
      badge: 'Step 7 of 7 — Settings',
      title: 'Customize Everything',
      desc: 'Head to <strong>Settings</strong> to configure your ElevenLabs API key, Presage capture interval, backend URL, and personalize the look with a custom accent color and light/dark theme — all saved in your browser.',
      illustration: `
        <div class="il-settings">
          <div class="il-color-wheel"></div>
          <div class="il-theme-cards">
            <div class="il-theme-card dark"></div>
            <div class="il-theme-card light"></div>
          </div>
        </div>`
    },
    {
      badge: "You're all set!",
      title: "Ready to SenseLense?",
      desc: 'You now know everything! Add your first client, start a session, and let the AI do the rest. Good luck out there — your customers\' emotions don\'t lie.',
      illustration: `
        <div class="il-done">
          ${Array.from({ length: 20 }, (_, i) => {
        const colors = ['#CC0000', '#22C55E', '#3B82F6', '#EAB308', '#EC4899', '#8B5CF6'];
        const c = colors[i % colors.length];
        const left = Math.random() * 100;
        const delay = Math.random() * 1.5;
        const size = 6 + Math.random() * 6;
        return `<div class="il-confetti-piece" style="left:${left}%;background:${c};width:${size}px;height:${size}px;animation-delay:${delay}s"></div>`;
      }).join('')}
          <div class="il-done-star">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="#f0b429" stroke="none"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
          </div>
        </div>`
    }
  ];

  /* ─────────────── STATE ─────────────── */
  let currentStep = 0;

  /* ─────────────── PROMPT MODAL ─────────────── */
  function buildPrompt() {
    if (document.getElementById('sl-tut-backdrop')) return;

    const backdrop = document.createElement('div');
    backdrop.id = 'sl-tut-backdrop';
    backdrop.innerHTML = `
      <div id="sl-tut-prompt">
        <div class="prompt-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--red,#CC0000)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <h2>Want a quick tour?</h2>
        <p>Take a 2-minute walkthrough of SenseLense and learn how to record sessions, track emotions, and review AI insights.</p>
        <div class="prompt-actions">
          <button class="btn-tut-begin" id="tut-begin-btn">Begin Tutorial</button>
          <button class="btn-tut-skip"  id="tut-skip-btn">Skip for now</button>
        </div>
      </div>`;

    document.body.appendChild(backdrop);
    requestAnimationFrame(() => backdrop.classList.add('visible'));

    document.getElementById('tut-begin-btn').onclick = () => { closePrompt(); startTutorial(); };
    document.getElementById('tut-skip-btn').onclick = closePrompt;
    backdrop.addEventListener('click', e => { if (e.target === backdrop) closePrompt(); });
  }

  function closePrompt() {
    const b = document.getElementById('sl-tut-backdrop');
    if (!b) return;
    b.classList.remove('visible');
    setTimeout(() => b.remove(), 400);
  }

  /* ─────────────── TUTORIAL OVERLAY ─────────────── */
  function buildOverlay() {
    if (document.getElementById('sl-tut-overlay')) return;
    const el = document.createElement('div');
    el.id = 'sl-tut-overlay';
    el.innerHTML = `
      <div id="sl-tut-card">
        <div class="tut-illustration" id="tut-il"></div>
        <div class="tut-content">
          <div class="tut-step-badge" id="tut-badge"></div>
          <div class="tut-title" id="tut-title"></div>
          <div class="tut-desc"  id="tut-desc"></div>
        </div>
        <div class="tut-footer">
          <div class="tut-dots" id="tut-dots"></div>
          <div class="tut-nav">
            <button class="btn-tut-prev" id="tut-prev">← Back</button>
            <button class="btn-tut-next" id="tut-next">Next →</button>
            <button class="btn-tut-done" id="tut-done" style="display:none">Finish</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(el);

    document.getElementById('tut-prev').onclick = () => navigate(-1);
    document.getElementById('tut-next').onclick = () => navigate(+1);
    document.getElementById('tut-done').onclick = closeTutorial;
    el.addEventListener('click', e => { if (e.target === el) closeTutorial(); });
  }

  function renderStep(idx, direction) {
    const card = document.getElementById('sl-tut-card');
    const badge = document.getElementById('tut-badge');
    const title = document.getElementById('tut-title');
    const desc = document.getElementById('tut-desc');
    const il = document.getElementById('tut-il');
    const dots = document.getElementById('tut-dots');
    const prevBtn = document.getElementById('tut-prev');
    const nextBtn = document.getElementById('tut-next');
    const doneBtn = document.getElementById('tut-done');
    const s = STEPS[idx];

    // Animate out
    if (direction !== 0) {
      card.classList.add('tut-anim-out');
      setTimeout(() => {
        card.classList.remove('tut-anim-out');
        fill();
        card.classList.add('tut-anim-in');
        setTimeout(() => card.classList.remove('tut-anim-in'), 400);
      }, 250);
    } else {
      fill();
    }

    function fill() {
      badge.textContent = s.badge;
      title.textContent = s.title;
      desc.innerHTML = s.desc;
      il.innerHTML = s.illustration;

      // Dots
      dots.innerHTML = STEPS.map((_, i) =>
        `<div class="tut-dot${i === idx ? ' active' : ''}" data-i="${i}"></div>`
      ).join('');
      dots.querySelectorAll('.tut-dot').forEach(d => {
        d.onclick = () => { currentStep = +d.dataset.i; renderStep(currentStep, 1); };
      });

      prevBtn.style.display = idx === 0 ? 'none' : '';
      nextBtn.style.display = idx === STEPS.length - 1 ? 'none' : '';
      doneBtn.style.display = idx === STEPS.length - 1 ? '' : 'none';
    }
  }

  function navigate(dir) {
    const next = currentStep + dir;
    if (next < 0 || next >= STEPS.length) return;
    currentStep = next;
    renderStep(currentStep, dir);
  }

  function startTutorial() {
    currentStep = 0;
    buildOverlay();
    renderStep(0, 0);
    const overlay = document.getElementById('sl-tut-overlay');
    requestAnimationFrame(() => overlay.classList.add('visible'));
  }

  function closeTutorial() {
    const overlay = document.getElementById('sl-tut-overlay');
    if (!overlay) return;
    overlay.classList.remove('visible');
    setTimeout(() => overlay.remove(), 450);
  }

  /* ─────────────── GLOBAL API ─────────────── */
  window.SLTutorial = { open: buildPrompt, start: startTutorial, close: closeTutorial };
})();
