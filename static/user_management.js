// User Management modal — shared across index.html, training_sets.html, training_runs.html.
// Self-contained: does not depend on script.js globals.
//
// TB-US-041 (2026-10-15): user management v2 — hard delete w/ confirmation,
// reactivate, inline email edit, bulk ops, audit log viewer tab, self-action
// protection UX. Backend from TB-US-017.

(function () {
    const API_BASE = window.location.origin;
    const USER_TYPES = ['super', 'chat', 'training'];
    const TAB_STORAGE_KEY = 'um_last_tab';
    const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    // Populated when the modal opens — used to disable self-action buttons.
    let currentUsername = null;
    // Current cache of user list for bulk-op selection.
    let currentUsers = [];
    // Selected usernames for bulk ops.
    let selected = new Set();

    function token() {
        return sessionStorage.getItem('session_token');
    }

    function authHeaders(extra) {
        const h = { 'Authorization': `Bearer ${token()}` };
        if (extra) Object.assign(h, extra);
        return h;
    }

    function escapeHtml(s) {
        if (s === null || s === undefined) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatDate(iso) {
        if (!iso) return '—';
        try {
            const d = new Date(iso);
            return d.toLocaleString();
        } catch (e) {
            return iso;
        }
    }

    function injectModal() {
        if (document.getElementById('user-mgmt-modal')) return;
        const wrap = document.createElement('div');
        wrap.innerHTML = `
<div id="user-mgmt-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.6); z-index: 3000; justify-content: center; align-items: center;">
    <div style="background: white; border-radius: 10px; padding: 25px; max-width: 1200px; width: 94%; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 12px; border-bottom: 2px solid #e0e0e0;">
            <h2 style="margin: 0; color: #CC785C;">👥 User Management</h2>
            <button onclick="closeUserManagement()" style="padding: 8px 16px; background: #999; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 1em;">Close</button>
        </div>

        <!-- Tab bar -->
        <div style="display: flex; gap: 2px; margin-bottom: 15px; border-bottom: 2px solid #e0e0e0;">
            <button id="um-tab-users" onclick="window.__umSwitchTab('users')" style="padding: 10px 20px; background: #CC785C; color: white; border: none; border-radius: 5px 5px 0 0; cursor: pointer; font-size: 0.95em; font-weight: bold;">Users</button>
            <button id="um-tab-audit" onclick="window.__umSwitchTab('audit')" style="padding: 10px 20px; background: #f5f5f5; color: #555; border: none; border-radius: 5px 5px 0 0; cursor: pointer; font-size: 0.95em;">Audit Log</button>
        </div>

        <div id="user-mgmt-status" style="display: none; margin-bottom: 15px; padding: 10px 14px; border-radius: 5px; font-size: 0.95em;"></div>

        <!-- Users tab panel -->
        <div id="um-panel-users">
            <details id="user-mgmt-create" style="margin-bottom: 20px; padding: 15px; background: rgba(204, 120, 92, 0.06); border-left: 4px solid #CC785C; border-radius: 5px;">
                <summary style="cursor: pointer; font-weight: bold; color: #CC785C; font-size: 1.05em;">➕ Create New User</summary>
                <div style="margin-top: 15px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div>
                        <label style="display: block; font-size: 0.9em; color: #555; margin-bottom: 4px;">Username</label>
                        <input id="um-new-username" type="text" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.9em; color: #555; margin-bottom: 4px;">Password</label>
                        <input id="um-new-password" type="text" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-family: monospace;">
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.9em; color: #555; margin-bottom: 4px;">User Type</label>
                        <select id="um-new-type" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                            <option value="chat">chat</option>
                            <option value="training">training</option>
                            <option value="super">super</option>
                        </select>
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.9em; color: #555; margin-bottom: 4px;">Email (optional)</label>
                        <input id="um-new-email" type="email" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                        <div id="um-new-email-error" style="display: none; margin-top: 4px; font-size: 0.85em; color: #c62828;"></div>
                    </div>
                </div>
                <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
                    <button onclick="createUserSubmit()" style="padding: 8px 18px; background: #CC785C; color: white; border: none; border-radius: 5px; cursor: pointer;">Create User</button>
                </div>
            </details>

            <!-- Bulk-op toolbar; surfaces when any row is checked -->
            <div id="um-bulk-toolbar" style="display: none; margin-bottom: 10px; padding: 10px 14px; background: #fff8e1; border: 1px solid #ffcc80; border-radius: 5px; display: none; align-items: center; justify-content: space-between; gap: 10px;">
                <span id="um-bulk-count" style="font-size: 0.95em; color: #555;"></span>
                <div style="display: flex; gap: 8px;">
                    <button onclick="window.__umBulk('deactivate')" style="padding: 6px 12px; background: #f9a825; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">Deactivate selected</button>
                    <button onclick="window.__umBulk('activate')" style="padding: 6px 12px; background: #43a047; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">Activate selected</button>
                    <button onclick="window.__umBulk('delete')" style="padding: 6px 12px; background: #d32f2f; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em;">Delete selected…</button>
                </div>
            </div>

            <div id="user-mgmt-list-wrap">
                <p style="color: #999;">Loading users…</p>
            </div>
        </div>

        <!-- Audit log tab panel -->
        <div id="um-panel-audit" style="display: none;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #555; font-size: 1em;">Audit Log — newest first (last 200 entries)</h3>
                <button onclick="window.__umLoadAudit()" style="padding: 6px 12px; background: #CC785C; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em;">Refresh</button>
            </div>
            <div id="user-mgmt-audit-wrap">
                <p style="color: #999;">Loading audit log…</p>
            </div>
        </div>
    </div>

    <!-- Confirmation sub-modal -->
    <div id="um-confirm-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); z-index: 3100; justify-content: center; align-items: center;">
        <div style="background: white; border-radius: 10px; padding: 25px; max-width: 500px; width: 90%; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);">
            <h3 id="um-confirm-title" style="margin: 0 0 15px 0; color: #c62828;">Delete permanently?</h3>
            <div id="um-confirm-body" style="margin-bottom: 20px; color: #333; line-height: 1.5;"></div>
            <div style="display: flex; justify-content: flex-end; gap: 10px;">
                <button onclick="window.__umConfirmCancel()" style="padding: 8px 16px; background: #999; color: white; border: none; border-radius: 5px; cursor: pointer;">Cancel</button>
                <button id="um-confirm-ok" style="padding: 8px 16px; background: #d32f2f; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">Delete permanently</button>
            </div>
        </div>
    </div>

    <!-- Edit user sub-modal (R13/AC14) -->
    <div id="um-edit-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); z-index: 3100; justify-content: center; align-items: center;">
        <div style="background: white; border-radius: 10px; padding: 25px; max-width: 500px; width: 90%; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);">
            <h3 style="margin: 0 0 15px 0; color: #CC785C;">Edit user: <span id="um-edit-username" style="font-family: monospace; color: #333;"></span></h3>
            <div style="margin-bottom: 15px;">
                <label style="display: block; font-size: 0.9em; color: #555; margin-bottom: 4px;">Email</label>
                <input id="um-edit-email" type="email" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                <div id="um-edit-email-error" style="display: none; margin-top: 4px; font-size: 0.85em; color: #c62828;"></div>
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; font-size: 0.9em; color: #555; margin-bottom: 4px;">User Type</label>
                <select id="um-edit-type" style="width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box;">
                    <option value="chat">chat</option>
                    <option value="training">training</option>
                    <option value="super">super</option>
                </select>
                <div id="um-edit-type-note" style="display: none; margin-top: 4px; font-size: 0.85em; color: #999;">Cannot change your own user type.</div>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px;">
                <button onclick="window.__umEditCancel()" style="padding: 8px 16px; background: #999; color: white; border: none; border-radius: 5px; cursor: pointer;">Cancel</button>
                <button onclick="window.__umEditSave()" style="padding: 8px 16px; background: #CC785C; color: white; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;">Save</button>
            </div>
        </div>
    </div>
</div>`;
        document.body.appendChild(wrap.firstElementChild);
    }

    function showStatus(msg, kind) {
        const el = document.getElementById('user-mgmt-status');
        if (!el) return;
        const colors = {
            success: { bg: '#e8f5e9', fg: '#2e7d32', border: '#66bb6a' },
            error:   { bg: '#ffebee', fg: '#c62828', border: '#ef5350' },
            info:    { bg: '#e3f2fd', fg: '#1565c0', border: '#42a5f5' }
        };
        const c = colors[kind] || colors.info;
        el.style.background = c.bg;
        el.style.color = c.fg;
        el.style.border = `1px solid ${c.border}`;
        el.textContent = msg;
        el.style.display = 'block';
        clearTimeout(showStatus._t);
        showStatus._t = setTimeout(() => { el.style.display = 'none'; }, 5000);
    }

    function switchTab(name) {
        const usersBtn = document.getElementById('um-tab-users');
        const auditBtn = document.getElementById('um-tab-audit');
        const usersPanel = document.getElementById('um-panel-users');
        const auditPanel = document.getElementById('um-panel-audit');
        if (!usersBtn || !auditBtn) return;

        const active = (btn) => { btn.style.background = '#CC785C'; btn.style.color = 'white'; btn.style.fontWeight = 'bold'; };
        const inactive = (btn) => { btn.style.background = '#f5f5f5'; btn.style.color = '#555'; btn.style.fontWeight = 'normal'; };

        if (name === 'audit') {
            active(auditBtn); inactive(usersBtn);
            usersPanel.style.display = 'none';
            auditPanel.style.display = 'block';
            loadAuditLog();
        } else {
            active(usersBtn); inactive(auditBtn);
            auditPanel.style.display = 'none';
            usersPanel.style.display = 'block';
            // Users panel content is already loaded by open; only refresh if stale
            if (!currentUsers.length) loadUsers();
        }
        sessionStorage.setItem(TAB_STORAGE_KEY, name);
    }

    async function loadUsers() {
        const wrap = document.getElementById('user-mgmt-list-wrap');
        wrap.innerHTML = '<p style="color: #999;">Loading users…</p>';
        try {
            const resp = await fetch(`${API_BASE}/users`, { headers: authHeaders() });
            if (!resp.ok) {
                if (resp.status === 401 || resp.status === 403) {
                    wrap.innerHTML = '<p style="color: #c62828;">Access denied. Super user privileges required.</p>';
                    return;
                }
                const t = await resp.text();
                wrap.innerHTML = `<p style="color: #c62828;">Failed to load users: ${escapeHtml(t)}</p>`;
                return;
            }
            const data = await resp.json();
            currentUsers = data.users || [];
            selected.clear();
            updateBulkToolbar();
            renderUsers(currentUsers);
        } catch (e) {
            wrap.innerHTML = `<p style="color: #c62828;">Error: ${escapeHtml(e.message)}</p>`;
        }
    }

    function renderUsers(users) {
        const wrap = document.getElementById('user-mgmt-list-wrap');
        if (!users.length) {
            wrap.innerHTML = '<p style="color: #999;">No users found.</p>';
            return;
        }
        const rows = users.map(u => {
            const isSelf = (u.username === currentUsername);
            const checkedAttr = selected.has(u.username) ? 'checked' : '';

            const activeBadge = u.active
                ? '<span style="color: #2e7d32; font-weight: bold; font-size: 0.85em;">● active</span>'
                : '<span style="color: #c62828; font-weight: bold; font-size: 0.85em; background: #ffebee; padding: 2px 8px; border-radius: 3px;">⊘ Deactivated</span>';

            const rowStyle = u.active ? '' : 'opacity: 0.65; background: #fafafa;';

            // TB-US-041 R12: single Actions dropdown. Options are
            // disabled contextually: self rows can't deactivate/delete,
            // active/deactivate option flips based on current status.
            // After selection, dropdown resets to the placeholder.
            const selfDisableAttr = isSelf ? 'disabled title="Cannot act on your own account"' : '';
            const activeToggleOption = u.active
                ? `<option value="deactivate" ${selfDisableAttr}>Deactivate</option>`
                : `<option value="activate">Reactivate</option>`;
            const deleteOption = `<option value="delete" ${selfDisableAttr}>Delete permanently…</option>`;

            return `
<tr style="${rowStyle}">
    <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">
        <input type="checkbox" ${checkedAttr} onchange="window.__umToggleSelect('${escapeHtml(u.username)}', this.checked)">
    </td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(u.username)}${isSelf ? ' <span style="color: #999; font-size: 0.8em;">(you)</span>' : ''}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(u.user_type)}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(u.email || '—')}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${activeBadge}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee; font-size: 0.85em; color: #666;">${escapeHtml(formatDate(u.last_login))}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">
        <select onchange="window.__umAction('${escapeHtml(u.username)}', this.value); this.value='';" style="padding: 5px 10px; border: 1px solid #CC785C; border-radius: 4px; cursor: pointer; background: white; color: #CC785C; font-size: 0.85em;">
            <option value="" selected>Actions ▾</option>
            <option value="reset">Reset Password</option>
            <option value="edit">Edit…</option>
            ${activeToggleOption}
            ${deleteOption}
        </select>
    </td>
</tr>`;
        }).join('');
        wrap.innerHTML = `
<table style="width: 100%; border-collapse: collapse;">
    <thead>
        <tr style="background: #f5f5f5;">
            <th style="text-align: center; padding: 10px 8px; border-bottom: 2px solid #ddd; width: 36px;">
                <input id="um-select-all" type="checkbox" onchange="window.__umSelectAll(this.checked)">
            </th>
            <th style="text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd;">Username</th>
            <th style="text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd;">Type</th>
            <th style="text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd;">Email</th>
            <th style="text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd;">Status</th>
            <th style="text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd;">Last Login</th>
            <th style="text-align: left; padding: 10px 8px; border-bottom: 2px solid #ddd;">Actions</th>
        </tr>
    </thead>
    <tbody>${rows}</tbody>
</table>`;
    }

    // TB-US-041 R12: dispatcher for the per-row Actions dropdown.
    function rowAction(username, action) {
        if (!action) return;
        switch (action) {
            case 'reset':      return resetPasswordSubmit(username);
            case 'edit':       return editUserStart(username);
            case 'activate':   return setActiveSubmit(username, true);
            case 'deactivate': return setActiveSubmit(username, false);
            case 'delete':     return hardDeleteStart(username);
            default:
                showStatus(`Unknown action: ${action}`, 'error');
        }
    }

    // TB-US-041 R13: Edit user modal (email + user_type combined).
    let editingUsername = null;
    let editingOriginal = { email: '', user_type: '' };

    function editUserStart(username) {
        const u = currentUsers.find(x => x.username === username);
        if (!u) return;
        const isSelf = (u.username === currentUsername);
        editingUsername = username;
        editingOriginal = {
            email: u.email || '',
            user_type: u.user_type,
        };

        document.getElementById('um-edit-username').textContent = username;
        const emailInput = document.getElementById('um-edit-email');
        const typeSelect = document.getElementById('um-edit-type');
        const typeNote = document.getElementById('um-edit-type-note');
        const errBox = document.getElementById('um-edit-email-error');

        emailInput.value = u.email || '';
        typeSelect.value = u.user_type;
        if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

        // TB-US-041 R13 / AC15: self-row — email editable, type read-only.
        if (isSelf) {
            typeSelect.disabled = true;
            typeSelect.style.opacity = '0.5';
            typeSelect.style.cursor = 'not-allowed';
            if (typeNote) typeNote.style.display = 'block';
        } else {
            typeSelect.disabled = false;
            typeSelect.style.opacity = '1';
            typeSelect.style.cursor = 'pointer';
            if (typeNote) typeNote.style.display = 'none';
        }

        const modal = document.getElementById('um-edit-modal');
        if (modal) modal.style.display = 'flex';
        setTimeout(() => emailInput.focus(), 50);
    }

    function editUserCancel() {
        const modal = document.getElementById('um-edit-modal');
        if (modal) modal.style.display = 'none';
        editingUsername = null;
    }

    async function editUserSave() {
        if (!editingUsername) return;
        const emailInput = document.getElementById('um-edit-email');
        const typeSelect = document.getElementById('um-edit-type');
        const errBox = document.getElementById('um-edit-email-error');

        const newEmail = (emailInput.value || '').trim();
        const newType = typeSelect.value;

        // Inline email validation (AC16)
        if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }
        if (newEmail && !EMAIL_RE.test(newEmail)) {
            if (errBox) {
                errBox.textContent = 'Not a valid email address.';
                errBox.style.display = 'block';
            }
            return;
        }

        // Determine which fields changed
        const emailChanged = (newEmail !== (editingOriginal.email || ''));
        const typeChanged = !typeSelect.disabled && (newType !== editingOriginal.user_type);

        if (!emailChanged && !typeChanged) {
            editUserCancel();
            return;
        }

        const username = editingUsername;
        const errors = [];

        try {
            if (emailChanged) {
                const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}/email`, {
                    method: 'PUT',
                    headers: authHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ email: newEmail || null })
                });
                if (!resp.ok) {
                    const data = await resp.json().catch(() => ({}));
                    errors.push(`email: ${data.detail || resp.status}`);
                }
            }
            if (typeChanged) {
                const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}/type`, {
                    method: 'PUT',
                    headers: authHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({ user_type: newType })
                });
                if (!resp.ok) {
                    const data = await resp.json().catch(() => ({}));
                    errors.push(`user_type: ${data.detail || resp.status}`);
                }
            }
        } catch (e) {
            errors.push(`network error: ${e.message}`);
        }

        if (errors.length) {
            showStatus(`Edit failed — ${errors.join('; ')}`, 'error');
        } else {
            const changedParts = [];
            if (emailChanged) changedParts.push('email');
            if (typeChanged) changedParts.push('type');
            showStatus(`Updated ${changedParts.join(' + ')} for '${username}'.`, 'success');
        }
        editUserCancel();
        loadUsers();
    }

    function updateBulkToolbar() {
        const bar = document.getElementById('um-bulk-toolbar');
        const count = document.getElementById('um-bulk-count');
        if (!bar || !count) return;
        if (selected.size === 0) {
            bar.style.display = 'none';
            return;
        }
        bar.style.display = 'flex';
        count.textContent = `${selected.size} selected: ${Array.from(selected).join(', ')}`;
    }

    function toggleSelect(username, checked) {
        if (checked) selected.add(username);
        else selected.delete(username);
        updateBulkToolbar();
    }

    function selectAll(checked) {
        selected.clear();
        if (checked) {
            currentUsers.forEach(u => {
                // Don't bulk-select self
                if (u.username !== currentUsername) selected.add(u.username);
            });
        }
        renderUsers(currentUsers);
        updateBulkToolbar();
    }

    // --- Create user with inline email validation ---
    async function createUserSubmit() {
        const username = document.getElementById('um-new-username').value.trim();
        const password = document.getElementById('um-new-password').value;
        const user_type = document.getElementById('um-new-type').value;
        const emailRaw = document.getElementById('um-new-email').value.trim();
        const errBox = document.getElementById('um-new-email-error');

        // Clear previous validation error
        if (errBox) { errBox.style.display = 'none'; errBox.textContent = ''; }

        if (!username || !password) {
            showStatus('Username and password are required.', 'error');
            return;
        }
        // Inline email validation
        if (emailRaw && !EMAIL_RE.test(emailRaw)) {
            if (errBox) {
                errBox.textContent = 'Not a valid email address.';
                errBox.style.display = 'block';
            }
            return;
        }

        const email = emailRaw || null;
        try {
            const resp = await fetch(`${API_BASE}/users`, {
                method: 'POST',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ username, password, user_type, email })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Failed to create user (${resp.status})`, 'error');
                return;
            }
            showStatus(`User '${username}' created.`, 'success');
            document.getElementById('um-new-username').value = '';
            document.getElementById('um-new-password').value = '';
            document.getElementById('um-new-email').value = '';
            document.getElementById('um-new-type').value = 'chat';
            loadUsers();
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
        }
    }

    async function changeUserTypeSubmit(username, newType) {
        if (!confirm(`Change user '${username}' to type '${newType}'?`)) {
            loadUsers();
            return;
        }
        try {
            const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}/type`, {
                method: 'PUT',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ user_type: newType })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Failed to change type (${resp.status})`, 'error');
                loadUsers();
                return;
            }
            showStatus(`Type updated for '${username}' → ${newType}.`, 'success');
            loadUsers();
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
            loadUsers();
        }
    }

    async function resetPasswordSubmit(username) {
        const pw = prompt(`New password for '${username}':`);
        if (pw === null) return;
        if (!pw) {
            showStatus('Password cannot be empty.', 'error');
            return;
        }
        try {
            const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}/password`, {
                method: 'PUT',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ new_password: pw })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Failed to reset password (${resp.status})`, 'error');
                return;
            }
            showStatus(`Password reset for '${username}'.`, 'success');
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
        }
    }

    // TB-US-041 R2: symmetric activate/deactivate via PUT /users/{u}/active
    async function setActiveSubmit(username, active) {
        const verb = active ? 'reactivate' : 'deactivate';
        if (!confirm(`${active ? 'Reactivate' : 'Deactivate'} user '${username}'?`)) return;
        try {
            const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}/active`, {
                method: 'PUT',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ active })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Failed to ${verb} (${resp.status})`, 'error');
                return;
            }
            showStatus(`User '${username}' ${active ? 'reactivated' : 'deactivated'}.`, 'success');
            loadUsers();
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
        }
    }

    // TB-US-041 R1: hard delete with confirmation modal
    function hardDeleteStart(username) {
        showConfirmModal(
            'Delete permanently?',
            `This will permanently remove user <strong>${escapeHtml(username)}</strong> from the database, including their created_at and last_login history. This action cannot be undone.<br><br>For a reversible disable, use <em>Deactivate</em> instead.`,
            () => hardDeleteCommit(username)
        );
    }

    async function hardDeleteCommit(username) {
        try {
            const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}?permanent=true`, {
                method: 'DELETE',
                headers: authHeaders()
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Failed to delete (${resp.status})`, 'error');
                return;
            }
            showStatus(`User '${username}' permanently deleted.`, 'success');
            loadUsers();
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
        }
    }

    // (Inline email click-to-edit was removed by TB-US-041 R14; email
    // edits now flow through the Edit modal — see editUserStart.)

    // TB-US-041 R4: bulk operations
    function bulkStart(action) {
        if (selected.size === 0) {
            showStatus('No users selected.', 'error');
            return;
        }
        const names = Array.from(selected);
        if (action === 'delete') {
            showConfirmModal(
                `Delete ${names.length} user${names.length === 1 ? '' : 's'} permanently?`,
                `This will permanently remove the following ${names.length} user${names.length === 1 ? '' : 's'}:<br><br><strong>${names.map(escapeHtml).join(', ')}</strong><br><br>This action cannot be undone.`,
                () => bulkCommit(action, names)
            );
        } else {
            bulkCommit(action, names);
        }
    }

    async function bulkCommit(action, usernames) {
        try {
            const resp = await fetch(`${API_BASE}/admin/bulk`, {
                method: 'POST',
                headers: authHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({ action, usernames })
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Bulk ${action} failed (${resp.status})`, 'error');
                return;
            }
            const parts = [`${data.succeeded} succeeded`];
            if (data.failed > 0) parts.push(`${data.failed} failed`);
            // Collect error reasons
            const errReasons = [];
            if (data.outcomes) {
                Object.entries(data.outcomes).forEach(([u, out]) => {
                    if (out.status === 'error') errReasons.push(`${u}: ${out.error}`);
                });
            }
            const summary = `Bulk ${action}: ${parts.join(', ')}.`
                + (errReasons.length ? ' Failures: ' + errReasons.join('; ') : '');
            showStatus(summary, data.failed === 0 ? 'success' : 'info');
            selected.clear();
            loadUsers();
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
        }
    }

    // Confirmation modal
    let currentConfirmOk = null;
    function showConfirmModal(title, bodyHtml, onConfirm) {
        const modal = document.getElementById('um-confirm-modal');
        const titleEl = document.getElementById('um-confirm-title');
        const bodyEl = document.getElementById('um-confirm-body');
        const okBtn = document.getElementById('um-confirm-ok');
        if (!modal) return;
        titleEl.textContent = title;
        bodyEl.innerHTML = bodyHtml;
        currentConfirmOk = onConfirm;
        // Rebind the OK handler (fresh each time)
        okBtn.onclick = () => {
            modal.style.display = 'none';
            if (currentConfirmOk) currentConfirmOk();
            currentConfirmOk = null;
        };
        modal.style.display = 'flex';
    }

    function confirmCancel() {
        const modal = document.getElementById('um-confirm-modal');
        if (modal) modal.style.display = 'none';
        currentConfirmOk = null;
    }

    // TB-US-041 R6: audit log viewer
    async function loadAuditLog() {
        const wrap = document.getElementById('user-mgmt-audit-wrap');
        wrap.innerHTML = '<p style="color: #999;">Loading audit log…</p>';
        try {
            const resp = await fetch(`${API_BASE}/admin/audit-log?limit=200`, { headers: authHeaders() });
            if (!resp.ok) {
                const t = await resp.text();
                wrap.innerHTML = `<p style="color: #c62828;">Failed to load audit log: ${escapeHtml(t)}</p>`;
                return;
            }
            const data = await resp.json();
            renderAuditLog(data.entries || []);
        } catch (e) {
            wrap.innerHTML = `<p style="color: #c62828;">Error: ${escapeHtml(e.message)}</p>`;
        }
    }

    function renderAuditLog(entries) {
        const wrap = document.getElementById('user-mgmt-audit-wrap');
        if (!entries.length) {
            wrap.innerHTML = '<p style="color: #999;">No audit entries yet.</p>';
            return;
        }
        const rows = entries.map(e => {
            const detailsStr = (e.details && typeof e.details === 'object')
                ? JSON.stringify(e.details, null, 2)
                : (e.details || '');
            const detailsRow = detailsStr
                ? `<details style="margin-top: 4px;"><summary style="cursor: pointer; color: #CC785C; font-size: 0.85em;">details</summary><pre style="margin: 4px 0 0 0; padding: 8px; background: #f5f5f5; border-radius: 3px; font-size: 0.8em; white-space: pre-wrap; word-break: break-all;">${escapeHtml(detailsStr)}</pre></details>`
                : '';
            const success = e.success
                ? '<span style="color: #2e7d32; font-weight: bold;">✓</span>'
                : '<span style="color: #c62828; font-weight: bold;">✗</span>';
            return `
<tr>
    <td style="padding: 6px 8px; border-bottom: 1px solid #eee; font-size: 0.85em; color: #666; white-space: nowrap;">${escapeHtml(formatDate(e.timestamp))}</td>
    <td style="padding: 6px 8px; border-bottom: 1px solid #eee;">${escapeHtml(e.actor)}</td>
    <td style="padding: 6px 8px; border-bottom: 1px solid #eee;"><code style="background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 0.9em;">${escapeHtml(e.action)}</code></td>
    <td style="padding: 6px 8px; border-bottom: 1px solid #eee;">${escapeHtml(e.target || '—')}</td>
    <td style="padding: 6px 8px; border-bottom: 1px solid #eee; text-align: center;">${success}</td>
    <td style="padding: 6px 8px; border-bottom: 1px solid #eee;">${detailsRow}</td>
</tr>`;
        }).join('');
        wrap.innerHTML = `
<table style="width: 100%; border-collapse: collapse;">
    <thead>
        <tr style="background: #f5f5f5;">
            <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd;">Timestamp</th>
            <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd;">Actor</th>
            <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd;">Action</th>
            <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd;">Target</th>
            <th style="text-align: center; padding: 8px; border-bottom: 2px solid #ddd;">OK</th>
            <th style="text-align: left; padding: 8px; border-bottom: 2px solid #ddd;">Details</th>
        </tr>
    </thead>
    <tbody>${rows}</tbody>
</table>`;
    }

    // --- open / close ---

    async function openUserManagement() {
        injectModal();

        // Fetch authenticated username so we can disable self-action buttons
        try {
            const resp = await fetch(`${API_BASE}/auth/verify`, { headers: authHeaders() });
            if (resp.ok) {
                const d = await resp.json();
                currentUsername = d.username || null;
            }
        } catch (e) {
            // Not fatal — self-action protection will fall back to backend enforcement
        }

        const modal = document.getElementById('user-mgmt-modal');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';

        // Restore last-selected tab (R10)
        const lastTab = sessionStorage.getItem(TAB_STORAGE_KEY) || 'users';
        switchTab(lastTab);
    }

    function closeUserManagement() {
        const modal = document.getElementById('user-mgmt-modal');
        if (modal) modal.style.display = 'none';
        const confirmModal = document.getElementById('um-confirm-modal');
        if (confirmModal) confirmModal.style.display = 'none';
        document.body.style.overflow = '';
    }

    // Expose the handlers globally so inline onclick attrs can find them.
    window.openUserManagement = openUserManagement;
    window.closeUserManagement = closeUserManagement;
    window.createUserSubmit = createUserSubmit;
    window.changeUserTypeSubmit = changeUserTypeSubmit;
    window.resetPasswordSubmit = resetPasswordSubmit;
    // deactivateUserSubmit retained for any legacy callers; new UI uses __umSetActive.
    window.deactivateUserSubmit = (u) => setActiveSubmit(u, false);

    // TB-US-041 internal handlers (prefixed to avoid namespace collisions)
    window.__umSwitchTab = switchTab;
    window.__umLoadAudit = loadAuditLog;
    window.__umSetActive = setActiveSubmit;
    window.__umHardDelete = hardDeleteStart;
    window.__umToggleSelect = toggleSelect;
    window.__umSelectAll = selectAll;
    window.__umBulk = bulkStart;
    window.__umConfirmCancel = confirmCancel;
    // Reopened additions (2026-10-15): Actions dropdown + Edit modal
    window.__umAction = rowAction;
    window.__umEditCancel = editUserCancel;
    window.__umEditSave = editUserSave;
})();
