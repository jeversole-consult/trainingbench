// TB-US-063: API key management modal.
// Self-contained; mirrors agent_management.js pattern.
// Super-only entry point from drawer-footer Admin group.

(function () {
    const API_BASE = window.location.origin;
    const MODAL_ID = 'tb-ak-modal';

    function token() { return sessionStorage.getItem('session_token'); }
    function authHeaders(extra) {
        const h = { 'Authorization': `Bearer ${token()}` };
        if (extra) Object.assign(h, extra);
        return h;
    }

    async function fetchJson(url, opts) {
        const res = await fetch(url, { ...(opts || {}), headers: authHeaders(opts && opts.headers) });
        if (!res.ok) {
            const txt = await res.text();
            throw new Error(txt || `${res.status} ${res.statusText}`);
        }
        return res.json();
    }

    function injectModal() {
        if (document.getElementById(MODAL_ID)) return;
        const el = document.createElement('div');
        el.id = MODAL_ID;
        el.style.cssText = [
            'position: fixed', 'top: 0', 'left: 0',
            'width: 100%', 'height: 100%',
            'background: rgba(0,0,0,0.4)', 'z-index: 3000',
            'display: none', 'align-items: center', 'justify-content: center',
        ].join('; ');
        el.innerHTML = `
<div style="background: white; border-radius: 12px; width: min(900px, 95vw); max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 10px 40px rgba(0,0,0,0.25);">
    <div style="padding: 16px 20px; border-bottom: 1px solid #E0E0E0; display: flex; justify-content: space-between; align-items: center;">
        <h2 style="margin: 0; color: #CC785C; font-size: 1.3em;">🔑 API Key Management</h2>
        <button id="tb-ak-close" style="background: none; border: 1px solid #E0E0E0; border-radius: 4px; padding: 2px 10px; cursor: pointer; font-size: 1.4em; line-height: 1; color: #555; font-weight: 600;" aria-label="Close" title="Close">&#x2715;</button>
    </div>
    <div style="padding: 16px 20px; border-bottom: 1px solid #F5F5F5; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div>
            <button id="tb-ak-new" style="padding: 8px 16px; background: #CC785C; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">+ Create key</button>
            <label style="margin-left: 16px; font-size: 0.9em; color: #555;">
                <input type="checkbox" id="tb-ak-show-revoked" checked style="vertical-align: middle;">
                Show revoked
            </label>
        </div>
        <div id="tb-ak-error" style="color: #c33; font-size: 0.9em; display: none;"></div>
    </div>
    <div id="tb-ak-reveal" style="display: none; padding: 16px 20px; border-bottom: 1px solid #F5F5F5; background: #FEF9F5;"></div>
    <div style="flex: 1; overflow-y: auto; padding: 16px 20px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.95em;">
            <thead>
                <tr style="border-bottom: 2px solid #E0E0E0; text-align: left;">
                    <th style="padding: 10px 8px;">Label</th>
                    <th style="padding: 10px 8px;">Prefix</th>
                    <th style="padding: 10px 8px;">Status</th>
                    <th style="padding: 10px 8px;">Created</th>
                    <th style="padding: 10px 8px;">Created by</th>
                    <th style="padding: 10px 8px;">Last used</th>
                    <th style="padding: 10px 8px;">Actions</th>
                </tr>
            </thead>
            <tbody id="tb-ak-tbody"></tbody>
        </table>
        <div id="tb-ak-empty" style="text-align: center; color: #999; padding: 40px 0; display: none;">No API keys yet. Click "+ Create key" to add one.</div>
    </div>
</div>`;
        document.body.appendChild(el);

        el.addEventListener('click', (e) => { if (e.target === el) closeModal(); });
        document.getElementById('tb-ak-close').onclick = closeModal;
        document.getElementById('tb-ak-new').onclick = showCreateForm;
        document.getElementById('tb-ak-show-revoked').onchange = refresh;
    }

    function openModal() {
        injectModal();
        document.getElementById(MODAL_ID).style.display = 'flex';
        document.getElementById('tb-ak-reveal').style.display = 'none';
        refresh();
    }

    function closeModal() {
        const el = document.getElementById(MODAL_ID);
        if (el) el.style.display = 'none';
    }

    function showError(msg) {
        const el = document.getElementById('tb-ak-error');
        el.textContent = msg || '';
        el.style.display = msg ? 'block' : 'none';
    }

    async function refresh() {
        showError('');
        const showRevoked = document.getElementById('tb-ak-show-revoked').checked;
        try {
            const data = await fetchJson(`${API_BASE}/api-keys?include_revoked=${showRevoked}`);
            renderKeys(data.keys || []);
        } catch (e) {
            showError('Failed to load keys: ' + e.message);
        }
    }

    function renderKeys(keys) {
        const tbody = document.getElementById('tb-ak-tbody');
        const empty = document.getElementById('tb-ak-empty');
        if (!keys.length) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';
        tbody.innerHTML = keys.map(k => {
            const isRevoked = !!k.revoked_at;
            const stateBadge = isRevoked
                ? '<span style="background: #fafafa; color: #777; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">revoked</span>'
                : '<span style="background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">active</span>';
            const actionsHtml = isRevoked
                ? '<span style="color: #999; font-size: 0.85em;">—</span>'
                : `<button onclick="window.__tbRevokeKey(${k.id}, '${escapeAttr(k.label)}')" style="padding: 4px 10px; background: white; border: 1px solid #E65100; color: #E65100; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(230,81,0,0.08)'" onmouseleave="this.style.background='white'">Revoke</button>`;
            return `
<tr style="border-bottom: 1px solid #F0F0F0;">
    <td style="padding: 10px 8px; font-weight: 500;">${escapeHtml(k.label)}</td>
    <td style="padding: 10px 8px; font-family: monospace; font-size: 0.9em; color: #666;">${escapeHtml(k.key_prefix)}&hellip;</td>
    <td style="padding: 10px 8px;">${stateBadge}</td>
    <td style="padding: 10px 8px; font-size: 0.85em; color: #666;">${k.created_at ? k.created_at.slice(0, 10) : ''}</td>
    <td style="padding: 10px 8px; font-size: 0.9em;">${escapeHtml(k.created_by || '')}</td>
    <td style="padding: 10px 8px; font-size: 0.85em; color: #666;">${k.last_used_at ? k.last_used_at.slice(0, 16).replace('T', ' ') : '—'}</td>
    <td style="padding: 10px 8px; white-space: nowrap;">${actionsHtml}</td>
</tr>`;
        }).join('');
    }

    function showCreateForm() {
        showError('');
        const label = window.prompt('Label for the new API key (e.g., "CI pipeline", "my-laptop", "sdk-v2"):');
        if (!label || !label.trim()) return;
        fetchJson(`${API_BASE}/api-keys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label: label.trim() }),
        })
            .then(key => {
                revealRawKey(key);
                refresh();
            })
            .catch(e => showError('Create failed: ' + e.message));
    }

    function revealRawKey(key) {
        const el = document.getElementById('tb-ak-reveal');
        el.innerHTML = `
<div style="padding: 10px 0;">
    <div style="font-weight: 600; color: #CC785C; margin-bottom: 6px;">🔑 New API key — copy it now</div>
    <div style="font-size: 0.85em; color: #c33; margin-bottom: 10px;">⚠ This is the only time this key is shown. If you lose it, you'll need to revoke and create a new one.</div>
    <div style="display: flex; gap: 8px; align-items: center;">
        <code id="tb-ak-raw" style="flex: 1; padding: 10px 14px; background: white; border: 1px solid #CC785C; border-radius: 6px; font-family: monospace; font-size: 0.95em; color: #333; word-break: break-all; user-select: all;">${escapeHtml(key.raw_key)}</code>
        <button onclick="window.__tbCopyRawKey()" style="padding: 10px 16px; background: #CC785C; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; white-space: nowrap;">Copy</button>
        <button onclick="document.getElementById('tb-ak-reveal').style.display='none'" style="padding: 10px 12px; background: white; border: 1px solid #999; color: #555; border-radius: 6px; cursor: pointer;" title="Dismiss (make sure you've copied the key first)">Done</button>
    </div>
    <div style="font-size: 0.8em; color: #666; margin-top: 8px;">Label: <strong>${escapeHtml(key.label)}</strong> &middot; Prefix: <code>${escapeHtml(key.key_prefix)}&hellip;</code></div>
</div>`;
        el.style.display = 'block';
    }

    window.__tbCopyRawKey = function () {
        const code = document.getElementById('tb-ak-raw');
        if (!code) return;
        const text = code.textContent;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).catch(() => {
                // fall through to selection method
                try {
                    const r = document.createRange();
                    r.selectNodeContents(code);
                    const sel = window.getSelection();
                    sel.removeAllRanges();
                    sel.addRange(r);
                    document.execCommand('copy');
                } catch (e) {}
            });
        }
    };

    window.__tbRevokeKey = function (id, label) {
        if (!window.confirm(`Revoke API key "${label}" (id=${id})?\n\nAny client using this key will stop working immediately. This cannot be undone.`)) return;
        showError('');
        fetchJson(`${API_BASE}/api-keys/${id}`, { method: 'DELETE' })
            .then(() => refresh())
            .catch(e => showError('Revoke failed: ' + e.message));
    };

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
    }
    function escapeAttr(s) {
        return String(s || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    window.openApiKeyManagement = openModal;
})();
