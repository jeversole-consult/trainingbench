// TB-US-066: active-run status strip.
// Primary operator-facing feature. Appears whenever ANY training run has
// status='running'. Shows live epoch / step / loss / elapsed. Visible on
// all pages (index.html, training_sets.html, training_runs.html).
// Super-only (non-super users can't launch training anyway).
//
// Polling cadence: 10s. Final-state visibility: 60s after a run
// completes / fails / cancels so operator sees the result on next
// return before the strip disappears.

(function () {
    const API_BASE = window.location.origin;
    const STRIP_ID = 'tb-active-run-strip';
    const POLL_INTERVAL_MS = 10 * 1000;      // 10s per TB-US-066 R4
    const FINAL_STATE_LINGER_MS = 60 * 1000; // 60s visibility after terminal state

    let pollTimer = null;
    let lingerUntil = null;
    let lingerRun = null;   // last-seen terminal run, kept for 60s

    function token() { return sessionStorage.getItem('session_token'); }

    function authHeaders() {
        return token() ? { 'Authorization': `Bearer ${token()}` } : {};
    }

    function elapsedFromStartedAt(startedAtIso) {
        try {
            const start = new Date(startedAtIso).getTime();
            const now = Date.now();
            const secs = Math.max(0, Math.floor((now - start) / 1000));
            const h = Math.floor(secs / 3600);
            const m = Math.floor((secs % 3600) / 60);
            const s = secs % 60;
            if (h > 0) return `${h}h ${m}m ${s.toString().padStart(2, '0')}s`;
            if (m > 0) return `${m}m ${s.toString().padStart(2, '0')}s`;
            return `${s}s`;
        } catch (e) { return '—'; }
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
    }

    function ensureStripElement() {
        let el = document.getElementById(STRIP_ID);
        if (el) return el;
        // Place after the hamburger (fixed top-left ~46px). We want this
        // under the header strip. For now, insert as the first child of
        // <body> and let its own styling pin it.
        el = document.createElement('div');
        el.id = STRIP_ID;
        el.style.cssText = [
            'position: sticky',
            'top: 0',
            'z-index: 1500',   // above most content, below drawer (2060)
            'margin: 0 0 10px 0',
            'display: none',
        ].join('; ');
        // Insert at top of body (safe fallback). If there's a main
        // container with id="app" or similar we could target that; most
        // TB pages have a header followed by content — sticky at the top
        // of body renders fine.
        document.body.insertBefore(el, document.body.firstChild);
        return el;
    }

    function renderStrip(run) {
        const el = ensureStripElement();
        if (!run) { el.style.display = 'none'; return; }

        const isActive = run.status === 'running';
        const label = isActive
            ? `⚙️ Training in progress: <strong>${escapeHtml(run.run_name)}</strong>`
            : `${statusEmoji(run.status)} Training ${escapeHtml(run.status)}: <strong>${escapeHtml(run.run_name)}</strong>`;

        // Live progress: pulled from the latest metric row (set by callback).
        // Falls back to the training_runs row's own fields.
        const parts = [];
        if (run.latest_step !== undefined && run.latest_step !== null) parts.push(`Step ${run.latest_step}`);
        if (run.latest_epoch !== undefined && run.latest_epoch !== null) parts.push(`Epoch ${Number(run.latest_epoch).toFixed(2)}`);
        if (run.latest_train_loss !== undefined && run.latest_train_loss !== null) parts.push(`Loss ${Number(run.latest_train_loss).toFixed(4)}`);
        const progressStr = parts.length ? parts.join(' · ') : (isActive ? 'Starting up…' : '');
        const elapsedStr = isActive
            ? `Elapsed ${elapsedFromStartedAt(run.started_at)}`
            : (run.duration_seconds ? `Duration ${run.duration_seconds}s` : '');

        const borderStyle = isActive
            ? 'border: 2px solid #CC785C; animation: tbPulseBorder 2s infinite;'
            : `border: 2px solid ${statusColor(run.status)};`;
        const bgStyle = isActive
            ? 'background: linear-gradient(90deg, rgba(204, 120, 92, 0.1) 0%, rgba(204, 120, 92, 0.04) 100%);'
            : `background: ${statusTint(run.status)};`;

        el.innerHTML = `
<style>
  @keyframes tbPulseBorder {
    0%, 100% { border-color: #CC785C; }
    50% { border-color: #e39a81; }
  }
</style>
<div style="${bgStyle} ${borderStyle} border-radius: 8px; padding: 10px 16px; display: flex; align-items: center; gap: 16px; font-size: 0.95em; flex-wrap: wrap;">
    <div style="flex: 1; min-width: 200px;">
        <div style="color: #333;">${label}</div>
        <div style="font-size: 0.85em; color: #666; margin-top: 2px;">
            ${escapeHtml(progressStr)}${progressStr && elapsedStr ? ' &middot; ' : ''}${escapeHtml(elapsedStr)}
        </div>
    </div>
    <a href="/static/training_runs.html#run/${run.id}" style="padding: 6px 14px; background: #CC785C; color: white; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.85em; white-space: nowrap;">View →</a>
    ${!isActive ? `<button onclick="document.getElementById('${STRIP_ID}').style.display='none'; window.__tbStripDismissed=${run.id}" title="Dismiss" style="background: none; border: 1px solid #ccc; border-radius: 4px; padding: 2px 10px; cursor: pointer; color: #555; font-size: 1.1em; line-height: 1;">&#x2715;</button>` : ''}
</div>`;
        el.style.display = 'block';
    }

    function statusEmoji(status) {
        return { completed: '✅', failed: '❌', stopped: '🛑' }[status] || 'ℹ️';
    }

    function statusColor(status) {
        return { completed: '#2e7d32', failed: '#c62828', stopped: '#616161' }[status] || '#999';
    }

    function statusTint(status) {
        return { completed: 'rgba(46, 125, 50, 0.06)', failed: 'rgba(198, 40, 40, 0.06)', stopped: 'rgba(97, 97, 97, 0.06)' }[status] || '#f5f5f5';
    }

    async function fetchLatestMetric(runId) {
        try {
            const res = await fetch(`${API_BASE}/training/runs/${runId}/metrics`, { headers: authHeaders() });
            if (!res.ok) return null;
            const data = await res.json();
            const metrics = data.metrics || [];
            return metrics.length ? metrics[metrics.length - 1] : null;
        } catch (e) { return null; }
    }

    async function poll() {
        if (!token()) return;
        // Super-only visibility; verify role first (cached per load).
        if (window.__tbStripRole === undefined) {
            try {
                const res = await fetch(`${API_BASE}/auth/verify`, { headers: authHeaders() });
                if (!res.ok) return;
                const data = await res.json();
                window.__tbStripRole = data.user_type;
            } catch (e) { return; }
        }
        if (window.__tbStripRole !== 'super') return;

        let run = null;
        try {
            const res = await fetch(`${API_BASE}/training/runs?status=running`, { headers: authHeaders() });
            if (!res.ok) return;
            const data = await res.json();
            const runs = data.training_runs || [];
            run = runs.length ? runs[0] : null;
        } catch (e) { return; }

        if (run) {
            // Augment with latest metric
            const metric = await fetchLatestMetric(run.id);
            if (metric) {
                run.latest_step = metric.step;
                run.latest_epoch = metric.epoch;
                run.latest_train_loss = metric.train_loss;
            }
            renderStrip(run);
            lingerRun = run;    // remember for 60s linger when it terminates
            lingerUntil = null;
            return;
        }

        // No active run. If we were just watching one, keep it visible for 60s
        // so operator sees the terminal state on their next return.
        if (lingerRun && lingerRun.status === 'running') {
            // The previously-active run just terminated. Fetch its final state.
            try {
                const res = await fetch(`${API_BASE}/training/runs/${lingerRun.id}`, { headers: authHeaders() });
                if (res.ok) {
                    const finalRun = await res.json();
                    // Dismissed by user?
                    if (window.__tbStripDismissed === finalRun.id) {
                        document.getElementById(STRIP_ID).style.display = 'none';
                        lingerRun = null; lingerUntil = null;
                        return;
                    }
                    lingerRun = finalRun;
                    lingerUntil = Date.now() + FINAL_STATE_LINGER_MS;
                }
            } catch (e) { /* ignore */ }
        }

        if (lingerRun && lingerUntil && Date.now() < lingerUntil) {
            if (window.__tbStripDismissed === lingerRun.id) {
                document.getElementById(STRIP_ID).style.display = 'none';
                return;
            }
            renderStrip(lingerRun);
        } else {
            lingerRun = null;
            lingerUntil = null;
            const el = document.getElementById(STRIP_ID);
            if (el) el.style.display = 'none';
        }
    }

    function start() {
        if (pollTimer) return;
        poll();
        pollTimer = setInterval(poll, POLL_INTERVAL_MS);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    // Expose for debug / testing
    window.__tbActiveRunStripPoll = poll;
})();
