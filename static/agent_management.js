// TB-US-048: Agent management modal (CRUD).
// Mirrors the TB-US-010/017/041 pattern: self-contained, injected into
// the DOM on first open, super-only.

(function () {
    const API_BASE = window.location.origin;
    const MODAL_ID = 'tb-agent-mgmt-modal';
    const NAME_RE = /^[a-z][a-z0-9_-]*$/;

    function token() {
        return sessionStorage.getItem('session_token');
    }

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
            'background: rgba(0,0,0,0.4)',
            'z-index: 3000',
            'display: none',
            'align-items: center', 'justify-content: center',
        ].join('; ');
        el.innerHTML = `
<div style="background: white; border-radius: 12px; width: min(900px, 95vw); max-height: 85vh; display: flex; flex-direction: column; box-shadow: 0 10px 40px rgba(0,0,0,0.25);">
    <div style="padding: 16px 20px; border-bottom: 1px solid #E0E0E0; display: flex; justify-content: space-between; align-items: center;">
        <h2 style="margin: 0; color: #CC785C; font-size: 1.3em;">🤖 Agent Management</h2>
        <button id="tb-am-close" style="background: none; border: 1px solid #E0E0E0; border-radius: 4px; padding: 2px 10px; cursor: pointer; font-size: 1.4em; line-height: 1; color: #555; font-weight: 600;" aria-label="Close" title="Close">&#x2715;</button>
    </div>
    <div style="padding: 16px 20px; border-bottom: 1px solid #F5F5F5; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap;">
        <div>
            <button id="tb-am-new" style="padding: 8px 16px; background: #CC785C; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">+ Create agent</button>
            <label style="margin-left: 16px; font-size: 0.9em; color: #555;">
                <input type="checkbox" id="tb-am-show-retired" checked style="vertical-align: middle;">
                Show retired
            </label>
        </div>
        <div id="tb-am-error" style="color: #c33; font-size: 0.9em; display: none;"></div>
    </div>
    <div id="tb-am-list-container" style="flex: 1; overflow-y: auto; padding: 16px 20px;">
        <table id="tb-am-table" style="width: 100%; border-collapse: collapse; font-size: 0.95em;">
            <thead>
                <tr style="border-bottom: 2px solid #E0E0E0; text-align: left;">
                    <th style="padding: 10px 8px;">Name</th>
                    <th style="padding: 10px 8px;">Display name</th>
                    <th style="padding: 10px 8px;">State</th>
                    <th style="padding: 10px 8px;">Created</th>
                    <th style="padding: 10px 8px;">Description</th>
                    <th style="padding: 10px 8px;">Actions</th>
                </tr>
            </thead>
            <tbody id="tb-am-tbody"></tbody>
        </table>
        <div id="tb-am-empty" style="text-align: center; color: #999; padding: 40px 0; display: none;">No agents yet. Click "+ Create agent" to add one.</div>
    </div>
</div>`;
        document.body.appendChild(el);

        el.addEventListener('click', (e) => {
            if (e.target === el) closeModal();
        });
        document.getElementById('tb-am-close').onclick = closeModal;
        document.getElementById('tb-am-new').onclick = showCreateForm;
        document.getElementById('tb-am-show-retired').onchange = refresh;
    }

    function openModal() {
        injectModal();
        document.getElementById(MODAL_ID).style.display = 'flex';
        refresh();
    }

    function closeModal() {
        const el = document.getElementById(MODAL_ID);
        if (el) el.style.display = 'none';
    }

    function showError(msg) {
        const el = document.getElementById('tb-am-error');
        el.textContent = msg || '';
        el.style.display = msg ? 'block' : 'none';
    }

    async function refresh() {
        showError('');
        const includeRetired = document.getElementById('tb-am-show-retired').checked;
        try {
            const data = await fetchJson(`${API_BASE}/agents?include_retired=${includeRetired}`);
            renderAgents(data.agents || []);
        } catch (e) {
            showError('Failed to load agents: ' + e.message);
        }
    }

    function renderAgents(agents) {
        const tbody = document.getElementById('tb-am-tbody');
        const empty = document.getElementById('tb-am-empty');
        if (!agents.length) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';
        tbody.innerHTML = agents.map(a => {
            const stateBadge = a.state === 'active'
                ? '<span style="background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">active</span>'
                : '<span style="background: #fafafa; color: #777; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">retired</span>';
            const actionsHtml = a.state === 'active'
                ? `<button onclick="window.__tbAgentRename('${escapeAttr(a.name)}')" style="padding: 4px 10px; margin-right: 4px; background: white; border: 1px solid #CC785C; color: #CC785C; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(204,120,92,0.08)'" onmouseleave="this.style.background='white'">Rename</button>
                   <button onclick="window.__tbAgentRetire('${escapeAttr(a.name)}')" style="padding: 4px 10px; background: white; border: 1px solid #E65100; color: #E65100; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(230,81,0,0.08)'" onmouseleave="this.style.background='white'">Retire</button>`
                : `<button onclick="window.__tbAgentReactivate('${escapeAttr(a.name)}')" style="padding: 4px 10px; background: white; border: 1px solid #1565C0; color: #1565C0; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(21,101,192,0.08)'" onmouseleave="this.style.background='white'">Reactivate</button>`;
            return `
<tr style="border-bottom: 1px solid #F0F0F0;">
    <td style="padding: 10px 8px; font-family: monospace;">${escapeHtml(a.name)}</td>
    <td style="padding: 10px 8px;">${escapeHtml(a.display_name || '')}</td>
    <td style="padding: 10px 8px;">${stateBadge}</td>
    <td style="padding: 10px 8px; font-size: 0.85em; color: #666;">${a.created_at ? a.created_at.slice(0, 10) : ''}</td>
    <td style="padding: 10px 8px; font-size: 0.9em; color: #666;">${escapeHtml(a.description || '')}</td>
    <td style="padding: 10px 8px; white-space: nowrap;">${actionsHtml}</td>
</tr>`;
        }).join('');
    }

    function showCreateForm() {
        showError('');
        const name = window.prompt('Agent name (lowercase, letters/digits/underscore/hyphen; e.g., "math-example"):');
        if (!name) return;
        if (!NAME_RE.test(name)) {
            showError(`Invalid name "${name}". Must match ${NAME_RE.source}`);
            return;
        }
        const displayName = window.prompt('Display name (optional; defaults to the slug):', name) || name;
        const description = window.prompt('Description (optional):', '') || '';
        fetchJson(`${API_BASE}/agents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, display_name: displayName, description }),
        })
            .then(() => refresh())
            .then(() => { if (window.__tbRefreshAgentSelector) window.__tbRefreshAgentSelector(); })
            .catch(e => showError('Create failed: ' + e.message));
    }

    window.__tbAgentRename = function (name) {
        showError('');
        const newName = window.prompt(`Rename "${name}" to:`, name);
        if (!newName || newName === name) return;
        if (!NAME_RE.test(newName)) {
            showError(`Invalid name "${newName}". Must match ${NAME_RE.source}`);
            return;
        }
        fetchJson(`${API_BASE}/agents/${encodeURIComponent(name)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_name: newName }),
        })
            .then(() => refresh())
            .then(() => { if (window.__tbRefreshAgentSelector) window.__tbRefreshAgentSelector(); })
            .catch(e => showError('Rename failed: ' + e.message));
    };

    window.__tbAgentRetire = function (name) {
        if (!window.confirm(`Retire agent "${name}"?\n\nRetiring preserves all data (snapshots, components) and marks the agent read-only. You can reactivate later.`)) return;
        showError('');
        fetchJson(`${API_BASE}/agents/${encodeURIComponent(name)}`, { method: 'DELETE' })
            .then(() => refresh())
            .then(() => { if (window.__tbRefreshAgentSelector) window.__tbRefreshAgentSelector(); })
            .catch(e => showError('Retire failed: ' + e.message));
    };

    window.__tbAgentReactivate = function (name) {
        if (!window.confirm(`Reactivate agent "${name}"?`)) return;
        showError('');
        fetchJson(`${API_BASE}/agents/${encodeURIComponent(name)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ state: 'active' }),
        })
            .then(() => refresh())
            .then(() => { if (window.__tbRefreshAgentSelector) window.__tbRefreshAgentSelector(); })
            .catch(e => showError('Reactivate failed: ' + e.message));
    };

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
    }

    function escapeAttr(s) {
        return String(s || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    window.openAgentManagement = openModal;
})();
