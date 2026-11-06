// TB auto-reload on version change.
// Polls /version/build every 30s. When the stamp differs from the one
// the page booted with, shows a top-right banner inviting the operator
// to reload. Zero manual cache tricks needed — a deploy announces
// itself visibly.
//
// Loaded on every app page (index, training_runs, training_sets,
// experiments, docs). Gate + login pages skip it — the banner would
// just be noise.

(function () {
    const POLL_INTERVAL_MS = 30 * 1000;
    const BANNER_ID = 'tb-version-banner';
    let bootStamp = null;
    let pollTimer = null;
    let dismissed = false;

    async function fetchStamp() {
        try {
            const res = await fetch('/version/build', { cache: 'no-store' });
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            return null;
        }
    }

    function stampsDiffer(a, b) {
        if (!a || !b) return false;
        // boot_time is the strongest signal (changes on every restart);
        // sha is a secondary check for pure static-file changes (though
        // those require a restart too in TB's deploy model).
        return a.boot_time !== b.boot_time || a.sha !== b.sha;
    }

    function showBanner() {
        if (document.getElementById(BANNER_ID)) return;
        if (dismissed) return;
        const el = document.createElement('div');
        el.id = BANNER_ID;
        el.style.cssText = [
            'position: fixed',
            'top: 14px',
            'right: 14px',
            'z-index: 10000',
            'background: #CC785C',
            'color: white',
            'padding: 10px 16px',
            'border-radius: 8px',
            'box-shadow: 0 6px 20px rgba(0,0,0,0.25)',
            'font-size: 0.9em',
            'display: flex',
            'align-items: center',
            'gap: 12px',
            'max-width: 400px',
            'animation: tbVerBannerIn 300ms ease-out',
        ].join('; ');
        el.innerHTML = `
            <style>
                @keyframes tbVerBannerIn { from { transform: translateY(-20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
            </style>
            <span>🆕 New TB version available</span>
            <button id="tb-ver-reload" style="background: white; color: #CC785C; border: none; padding: 6px 12px; border-radius: 6px; font-weight: 700; cursor: pointer; font-size: 0.9em;">Reload</button>
            <button id="tb-ver-dismiss" title="Dismiss until next reload" style="background: transparent; color: white; border: 1px solid rgba(255,255,255,0.4); padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.85em;">&times;</button>
        `;
        document.body.appendChild(el);
        document.getElementById('tb-ver-reload').onclick = () => {
            window.location.reload();
        };
        document.getElementById('tb-ver-dismiss').onclick = () => {
            dismissed = true;
            el.remove();
        };
    }

    async function poll() {
        const latest = await fetchStamp();
        if (!latest) return;
        if (bootStamp === null) {
            bootStamp = latest;
            return;
        }
        if (stampsDiffer(bootStamp, latest)) {
            showBanner();
        }
    }

    function start() {
        if (pollTimer) return;
        poll();
        pollTimer = setInterval(poll, POLL_INTERVAL_MS);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    // Expose for debug.
    window.__tbVersionCheck = { poll, bootStamp: () => bootStamp };
})();
