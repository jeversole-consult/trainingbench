// TB-US-095: Query-routes management modal.
// Reverse-port of stalite3's SL-US-010 "configurable query-routing
// for category-biased retrieval" UI. TB has had the backend
// (TB-US-040 cache + _maybe_augment_query, TB-US-033 GET/PUT
// /settings/query-routes) since Oct 2026 but never built the UI
// surface. Stalite built it in June 2026; we're porting the UI
// pattern verbatim, adapted to TB's drawer-admin-dropdown.
//
// Opens from drawer footer → Admin dropdown → "Query Routes".
// Super-only; drawer only shows the admin group to super users.

(function () {
    const API_BASE = window.location.origin;
    const MODAL_ID = 'tb-query-routes-modal';
    const EDITOR_ID = 'tb-query-route-editor';

    let _routes = [];
    let _editingIndex = null;   // null = add-new; integer = edit-existing
    let _savedAt = null;
    let _savedBy = null;

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
<div style="background: white; border-radius: 12px; width: min(1000px, 95vw); max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 10px 40px rgba(0,0,0,0.25);">
    <div style="padding: 16px 20px; border-bottom: 1px solid #E0E0E0; display: flex; justify-content: space-between; align-items: center;">
        <h2 style="margin: 0; color: #CC785C; font-size: 1.3em;">🧭 Query Routes</h2>
        <button id="tb-qr-close" style="background: none; border: 1px solid #E0E0E0; border-radius: 4px; padding: 2px 10px; cursor: pointer; font-size: 1.4em; line-height: 1; color: #555; font-weight: 600;" aria-label="Close" title="Close">&#x2715;</button>
    </div>
    <div style="padding: 16px 20px 0 20px;">
        <p style="color: #666; font-size: 0.9em; margin: 0 0 12px 0;">
            When a user question matches a route's pattern, the search string sent to ChromaDB is augmented with the route's phrase (the LLM still sees the original question). This biases retrieval toward the right category of content without users having to know prefix tricks.
        </p>
        <div style="padding: 10px 14px; background: rgba(204, 120, 92, 0.06); border-left: 3px solid #CC785C; border-radius: 4px; font-size: 0.85em; color: #555; margin-bottom: 14px;">
            💡 <strong>Match order matters.</strong> Routes are evaluated top-to-bottom; first pattern that matches wins. Put narrower routes above broader ones. Disabled routes are skipped.
        </div>
        <div id="tb-qr-error" style="color: #c33; font-size: 0.9em; display: none; margin-bottom: 10px;"></div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <button id="tb-qr-add" style="padding: 8px 16px; background: #CC785C; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">+ Add route</button>
            <span id="tb-qr-savedinfo" style="font-size: 0.85em; color: #888;"></span>
        </div>
    </div>
    <div id="tb-qr-list-container" style="flex: 1; overflow-y: auto; padding: 0 20px 16px 20px;">
        <table id="tb-qr-table" style="width: 100%; border-collapse: collapse; font-size: 0.95em;">
            <thead>
                <tr style="border-bottom: 2px solid #E0E0E0; text-align: left;">
                    <th style="padding: 10px 8px;">Name</th>
                    <th style="padding: 10px 8px;">Patterns</th>
                    <th style="padding: 10px 8px;">Augmentation</th>
                    <th style="padding: 10px 8px;">Position</th>
                    <th style="padding: 10px 8px; text-align: center;">Enabled</th>
                    <th style="padding: 10px 8px; text-align: right;">Actions</th>
                </tr>
            </thead>
            <tbody id="tb-qr-tbody"></tbody>
        </table>
        <div id="tb-qr-empty" style="text-align: center; color: #999; padding: 40px 0; display: none;">No routes configured. Click "+ Add route" to create one.</div>
    </div>
</div>`;
        document.body.appendChild(el);

        el.addEventListener('click', (e) => { if (e.target === el) closeModal(); });
        document.getElementById('tb-qr-close').onclick = closeModal;
        document.getElementById('tb-qr-add').onclick = () => openEditor(null);
    }

    function injectEditor() {
        if (document.getElementById(EDITOR_ID)) return;
        const el = document.createElement('div');
        el.id = EDITOR_ID;
        el.style.cssText = [
            'position: fixed', 'top: 0', 'left: 0',
            'width: 100%', 'height: 100%',
            'background: rgba(0,0,0,0.5)',
            'z-index: 3100',
            'display: none',
            'align-items: center', 'justify-content: center',
        ].join('; ');
        el.innerHTML = `
<div style="background: white; border-radius: 10px; padding: 24px; max-width: 640px; width: 92%; max-height: 88vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);">
    <h3 id="tb-qr-ed-title" style="margin-top: 0; color: #CC785C;">Add route</h3>

    <label style="display: block; font-weight: 600; margin: 12px 0 4px 0;">Name</label>
    <input type="text" id="tb-qr-ed-name" placeholder="e.g. corporate_directory" style="width: 100%; padding: 8px; border: 1px solid #E0E0E0; border-radius: 5px; box-sizing: border-box;">

    <label style="display: block; font-weight: 600; margin: 12px 0 4px 0;">Patterns (one regex per line, case-insensitive)</label>
    <textarea id="tb-qr-ed-patterns" rows="6" placeholder="^who\\s+is\\s+\n^what\\s+does\\s+\\w+(\\s+\\w+)?\\s+do" style="width: 100%; padding: 8px; border: 1px solid #E0E0E0; border-radius: 5px; font-family: 'Courier New', monospace; font-size: 0.9em; box-sizing: border-box;"></textarea>

    <label style="display: block; font-weight: 600; margin: 12px 0 4px 0;">Augmentation</label>
    <input type="text" id="tb-qr-ed-augmentation" placeholder="e.g. corporate directory: " style="width: 100%; padding: 8px; border: 1px solid #E0E0E0; border-radius: 5px; box-sizing: border-box;">

    <div style="display: flex; gap: 20px; margin-top: 12px; align-items: center;">
        <div>
            <label style="font-weight: 600; margin-right: 6px;">Position</label>
            <select id="tb-qr-ed-position" style="padding: 6px; border: 1px solid #E0E0E0; border-radius: 5px;">
                <option value="prefix">Prefix</option>
                <option value="suffix">Suffix</option>
            </select>
        </div>
        <label style="display: flex; align-items: center; gap: 6px;">
            <input type="checkbox" id="tb-qr-ed-enabled" checked>
            <span style="font-weight: 600;">Enabled</span>
        </label>
    </div>

    <div id="tb-qr-ed-error" style="margin-top: 12px; color: #c33; font-size: 0.9em;"></div>

    <div style="display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end;">
        <button id="tb-qr-ed-cancel" style="padding: 8px 16px; background: white; border: 1px solid #999; color: #555; border-radius: 6px; cursor: pointer;">Cancel</button>
        <button id="tb-qr-ed-save" style="padding: 8px 16px; background: #CC785C; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Save</button>
    </div>
</div>`;
        document.body.appendChild(el);

        el.addEventListener('click', (e) => { if (e.target === el) closeEditor(); });
        document.getElementById('tb-qr-ed-cancel').onclick = closeEditor;
        document.getElementById('tb-qr-ed-save').onclick = saveFromEditor;
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

    function openEditor(idx) {
        injectEditor();
        _editingIndex = idx;
        document.getElementById('tb-qr-ed-title').textContent = (idx === null || idx === undefined) ? 'Add route' : 'Edit route';
        const r = (idx !== null && idx !== undefined) ? (_routes[idx] || {}) : {};
        document.getElementById('tb-qr-ed-name').value = r.name || '';
        document.getElementById('tb-qr-ed-patterns').value = (r.patterns || []).join('\n');
        document.getElementById('tb-qr-ed-augmentation').value = r.augmentation || '';
        document.getElementById('tb-qr-ed-position').value = r.position || 'prefix';
        document.getElementById('tb-qr-ed-enabled').checked = r.enabled !== false;
        document.getElementById('tb-qr-ed-error').textContent = '';
        document.getElementById(EDITOR_ID).style.display = 'flex';
    }

    function closeEditor() {
        const el = document.getElementById(EDITOR_ID);
        if (el) el.style.display = 'none';
        _editingIndex = null;
    }

    function showError(msg) {
        const el = document.getElementById('tb-qr-error');
        if (!el) return;
        el.textContent = msg || '';
        el.style.display = msg ? 'block' : 'none';
    }

    function showEditorError(msg) {
        const el = document.getElementById('tb-qr-ed-error');
        if (el) el.textContent = msg || '';
    }

    async function refresh() {
        showError('');
        try {
            const data = await fetchJson(`${API_BASE}/settings/query-routes`);
            _routes = Array.isArray(data.routes) ? data.routes : [];
            _savedAt = data.saved_at || null;
            _savedBy = data.saved_by || null;
            renderRoutes();
        } catch (e) {
            showError('Failed to load routes: ' + e.message);
        }
    }

    function renderRoutes() {
        const tbody = document.getElementById('tb-qr-tbody');
        const empty = document.getElementById('tb-qr-empty');
        const savedinfo = document.getElementById('tb-qr-savedinfo');

        if (savedinfo) {
            savedinfo.textContent = (_savedAt && _savedBy)
                ? `Last saved ${_savedAt.slice(0, 10)} by ${_savedBy}`
                : '';
        }

        if (!_routes.length) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        empty.style.display = 'none';

        tbody.innerHTML = _routes.map((r, idx) => {
            const patterns = (r.patterns || []).map(escapeHtml).join('<br>');
            const enabledBadge = r.enabled !== false
                ? '<span style="background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">enabled</span>'
                : '<span style="background: #fafafa; color: #777; padding: 2px 8px; border-radius: 10px; font-size: 0.85em;">disabled</span>';
            return `
<tr style="border-bottom: 1px solid #F0F0F0; vertical-align: top;">
    <td style="padding: 10px 8px; font-family: monospace;">${escapeHtml(r.name)}</td>
    <td style="padding: 10px 8px; font-family: monospace; font-size: 0.85em; color: #555;">${patterns}</td>
    <td style="padding: 10px 8px;">${escapeHtml(r.augmentation || '')}</td>
    <td style="padding: 10px 8px; font-size: 0.85em; color: #666;">${escapeHtml(r.position || 'prefix')}</td>
    <td style="padding: 10px 8px; text-align: center;">${enabledBadge}</td>
    <td style="padding: 10px 8px; text-align: right; white-space: nowrap;">
        <button onclick="window.__tbQRToggle(${idx})" style="padding: 4px 10px; margin-right: 4px; background: white; border: 1px solid #555; color: #555; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(85,85,85,0.08)'" onmouseleave="this.style.background='white'">${r.enabled !== false ? 'Disable' : 'Enable'}</button>
        <button onclick="window.__tbQREdit(${idx})" style="padding: 4px 10px; margin-right: 4px; background: white; border: 1px solid #CC785C; color: #CC785C; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(204,120,92,0.08)'" onmouseleave="this.style.background='white'">Edit</button>
        <button onclick="window.__tbQRDelete(${idx})" style="padding: 4px 10px; background: white; border: 1px solid #E65100; color: #E65100; border-radius: 4px; cursor: pointer; font-size: 0.85em; font-weight: 500;" onmouseenter="this.style.background='rgba(230,81,0,0.08)'" onmouseleave="this.style.background='white'">Delete</button>
    </td>
</tr>`;
        }).join('');
    }

    async function putRoutes(newRoutes) {
        try {
            await fetchJson(`${API_BASE}/settings/query-routes`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ routes: newRoutes }),
            });
            await refresh();
        } catch (e) {
            showError('Save failed: ' + e.message);
        }
    }

    function saveFromEditor() {
        showEditorError('');
        const name = document.getElementById('tb-qr-ed-name').value.trim();
        const patterns = document.getElementById('tb-qr-ed-patterns').value
            .split('\n').map(s => s.trim()).filter(Boolean);
        const augmentation = document.getElementById('tb-qr-ed-augmentation').value;
        const position = document.getElementById('tb-qr-ed-position').value;
        const enabled = document.getElementById('tb-qr-ed-enabled').checked;

        if (!name) { showEditorError('Name is required.'); return; }
        if (!patterns.length) { showEditorError('At least one pattern is required.'); return; }
        if (!augmentation.trim()) { showEditorError('Augmentation is required.'); return; }
        if (position !== 'prefix' && position !== 'suffix') { showEditorError('Position must be prefix or suffix.'); return; }

        const route = { name, patterns, augmentation, position, enabled };
        const next = _routes.slice();
        if (_editingIndex === null || _editingIndex === undefined) {
            next.push(route);
        } else {
            next[_editingIndex] = route;
        }
        closeEditor();
        putRoutes(next);
    }

    window.__tbQRToggle = function (idx) {
        if (!_routes[idx]) return;
        const next = _routes.slice();
        next[idx] = { ...next[idx], enabled: !(next[idx].enabled !== false) };
        putRoutes(next);
    };

    window.__tbQREdit = function (idx) {
        openEditor(idx);
    };

    window.__tbQRDelete = function (idx) {
        if (!_routes[idx]) return;
        if (!confirm(`Delete route '${_routes[idx].name}'? This will be recorded in the audit log.`)) return;
        const next = _routes.slice();
        next.splice(idx, 1);
        putRoutes(next);
    };

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
    }

    window.openQueryRoutesManagement = openModal;
})();
