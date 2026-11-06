// TB-US-070: active-experiment status strip.
// Mirrors TB-US-066's active-run strip for experiments. Appears whenever
// any experiment has state='running'. Visible on index.html,
// training_sets.html, training_runs.html, experiments.html.
// Super-only (non-super users can't launch experiments).
//
// Polling cadence: 10s. Final-state visibility: 60s after an experiment
// completes / archives so operator sees the result on next return.
//
// Stacking with TB-US-066's training-run strip:
//   The training-run strip is sticky at top:0. This strip uses
//   position:relative so it appears naturally above/below without
//   overlapping. Trade-off: scrolls with content (vs sticky). The
//   strip's primary value is "something IS running" on page-load/return,
//   so scroll-away is acceptable.

(function () {
    const API_BASE = window.location.origin;
    const STRIP_ID = 'tb-active-experiment-strip';
    const POLL_INTERVAL_MS = 10 * 1000;      // R4
    const FINAL_STATE_LINGER_MS = 60 * 1000; // R6

    let pollTimer = null;
    let lingerUntil = null;
    let lingerExperiment = null;

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
        el = document.createElement('div');
        el.id = STRIP_ID;
        el.style.cssText = [
            'position: relative',
            'z-index: 1400',
            'margin: 0 0 10px 0',
            'display: none',
        ].join('; ');
        document.body.insertBefore(el, document.body.firstChild);
        return el;
    }

    function parseProgress(experiment) {
        if (!experiment.progress_json) return null;
        try { return JSON.parse(experiment.progress_json); }
        catch (e) { return null; }
    }

    function parseResults(experiment) {
        if (!experiment.results_json) return null;
        try { return JSON.parse(experiment.results_json); }
        catch (e) { return null; }
    }

    function stateColor(state) {
        return {
            running:   '#CC785C',
            completed: '#2e7d32',
            archived:  '#c62828',
            promoted:  '#1565C0',
        }[state] || '#999';
    }

    function stateTint(state) {
        return {
            completed: 'rgba(46, 125, 50, 0.06)',
            archived:  'rgba(198, 40, 40, 0.06)',
            promoted:  'rgba(21, 101, 192, 0.06)',
        }[state] || '#f5f5f5';
    }

    function renderStrip(experiment) {
        const el = ensureStripElement();
        if (!experiment) { el.style.display = 'none'; return; }

        const isActive = experiment.state === 'running';
        const label = isActive
            ? `🧪 Experiment running: <strong>${escapeHtml(experiment.label)}</strong>`
            : `${stateEmoji(experiment.state)} Experiment ${escapeHtml(experiment.state)}: <strong>${escapeHtml(experiment.label)}</strong>`;

        const parts = [];
        if (isActive) {
            const prog = parseProgress(experiment);
            if (prog && prog.total_samples) {
                parts.push(`Sample ${prog.current_sample}/${prog.total_samples}`);
                if (typeof prog.running_correct === 'number' && prog.current_sample > 0) {
                    const runningAcc = (prog.running_correct / prog.current_sample * 100).toFixed(1);
                    parts.push(`${runningAcc}% correct so far`);
                }
            }
        } else {
            const results = parseResults(experiment);
            if (results && results.metric && results.value !== null && results.value !== undefined) {
                parts.push(`${escapeHtml(results.metric)}=${typeof results.value === 'number' ? results.value.toFixed(3) : escapeHtml(String(results.value))}`);
            }
        }
        const progressStr = parts.join(' · ') || (isActive ? 'Starting up…' : '');

        const elapsedStr = isActive
            ? (experiment.started_at ? `Elapsed ${elapsedFromStartedAt(experiment.started_at)}` : '')
            : (experiment.started_at && experiment.completed_at
                ? `Duration ${elapsedFromStartedAt(experiment.started_at).replace('Elapsed ', '')}`
                : '');

        const borderStyle = isActive
            ? 'border: 2px solid #CC785C; animation: tbExpPulseBorder 2s infinite;'
            : `border: 2px solid ${stateColor(experiment.state)};`;
        const bgStyle = isActive
            ? 'background: linear-gradient(90deg, rgba(204, 120, 92, 0.1) 0%, rgba(204, 120, 92, 0.04) 100%);'
            : `background: ${stateTint(experiment.state)};`;

        el.innerHTML = `
<style>
  @keyframes tbExpPulseBorder {
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
    <a href="/static/experiments.html#experiment/${experiment.experiment_id}" style="padding: 6px 14px; background: #CC785C; color: white; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 0.85em; white-space: nowrap;">View →</a>
    ${!isActive ? `<button onclick="document.getElementById('${STRIP_ID}').style.display='none'; window.__tbExpStripDismissed=${experiment.experiment_id}" title="Dismiss" style="background: none; border: 1px solid #ccc; border-radius: 4px; padding: 2px 10px; cursor: pointer; color: #555; font-size: 1.1em; line-height: 1;">&#x2715;</button>` : ''}
</div>`;
        el.style.display = 'block';
    }

    function stateEmoji(state) {
        return { completed: '✅', archived: '🗄', promoted: '🎯', displaced: '↩️' }[state] || 'ℹ️';
    }

    async function poll() {
        if (!token()) return;
        if (window.__tbStripRole === undefined) {
            try {
                const res = await fetch(`${API_BASE}/auth/verify`, { headers: authHeaders() });
                if (!res.ok) return;
                const data = await res.json();
                window.__tbStripRole = data.user_type;
            } catch (e) { return; }
        }
        if (window.__tbStripRole !== 'super') return;

        let experiment = null;
        try {
            const res = await fetch(`${API_BASE}/experiments?state=running`, { headers: authHeaders() });
            if (!res.ok) return;
            const data = await res.json();
            const rows = data.experiments || [];
            experiment = rows.length ? rows[0] : null;
        } catch (e) { return; }

        if (experiment) {
            renderStrip(experiment);
            lingerExperiment = experiment;
            lingerUntil = null;
            return;
        }

        // Linger on the terminal state for 60s after a watched run ends.
        if (lingerExperiment && lingerExperiment.state === 'running') {
            try {
                const res = await fetch(`${API_BASE}/experiments/${lingerExperiment.experiment_id}`, { headers: authHeaders() });
                if (res.ok) {
                    const final = await res.json();
                    if (window.__tbExpStripDismissed === final.experiment_id) {
                        const el = document.getElementById(STRIP_ID);
                        if (el) el.style.display = 'none';
                        lingerExperiment = null; lingerUntil = null;
                        return;
                    }
                    lingerExperiment = final;
                    lingerUntil = Date.now() + FINAL_STATE_LINGER_MS;
                }
            } catch (e) { /* ignore */ }
        }

        if (lingerExperiment && lingerUntil && Date.now() < lingerUntil) {
            if (window.__tbExpStripDismissed === lingerExperiment.experiment_id) {
                const el = document.getElementById(STRIP_ID);
                if (el) el.style.display = 'none';
                return;
            }
            renderStrip(lingerExperiment);
        } else {
            lingerExperiment = null;
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }

    window.__tbActiveExperimentStripPoll = poll;
})();
