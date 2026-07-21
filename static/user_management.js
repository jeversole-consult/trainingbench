// User Management modal — shared across index.html, training_sets.html, training_runs.html.
// Self-contained: does not depend on script.js globals.

(function () {
    const API_BASE = window.location.origin;
    const USER_TYPES = ['super', 'chat', 'training'];

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
<div id="user-mgmt-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.6); z-index: 2000; justify-content: center; align-items: center;">
    <div style="background: white; border-radius: 10px; padding: 25px; max-width: 1100px; width: 94%; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 12px; border-bottom: 2px solid #e0e0e0;">
            <h2 style="margin: 0; color: #667eea;">👥 User Management</h2>
            <button onclick="closeUserManagement()" style="padding: 8px 16px; background: #999; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 1em;">Close</button>
        </div>

        <div id="user-mgmt-status" style="display: none; margin-bottom: 15px; padding: 10px 14px; border-radius: 5px; font-size: 0.95em;"></div>

        <details id="user-mgmt-create" style="margin-bottom: 20px; padding: 15px; background: rgba(102, 126, 234, 0.06); border-left: 4px solid #667eea; border-radius: 5px;">
            <summary style="cursor: pointer; font-weight: bold; color: #667eea; font-size: 1.05em;">➕ Create New User</summary>
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
                </div>
            </div>
            <div style="margin-top: 12px; display: flex; justify-content: flex-end;">
                <button onclick="createUserSubmit()" style="padding: 8px 18px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">Create User</button>
            </div>
        </details>

        <div id="user-mgmt-list-wrap">
            <p style="color: #999;">Loading users…</p>
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
            renderUsers(data.users || []);
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
            const typeOpts = USER_TYPES.map(t =>
                `<option value="${t}" ${t === u.user_type ? 'selected' : ''}>${t}</option>`
            ).join('');
            const active = u.active
                ? '<span style="color: #2e7d32; font-weight: bold;">active</span>'
                : '<span style="color: #999;">inactive</span>';
            const deactivateBtn = u.active
                ? `<button onclick="deactivateUserSubmit('${escapeHtml(u.username)}')" style="padding: 5px 10px; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em;">Deactivate</button>`
                : `<span style="font-size: 0.85em; color: #999;">—</span>`;
            return `
<tr>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(u.username)}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">
        <select onchange="changeUserTypeSubmit('${escapeHtml(u.username)}', this.value)" style="padding: 4px 6px; border: 1px solid #ccc; border-radius: 4px;">
            ${typeOpts}
        </select>
    </td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${escapeHtml(u.email || '')}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">${active}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee; font-size: 0.85em; color: #666;">${escapeHtml(formatDate(u.last_login))}</td>
    <td style="padding: 8px; border-bottom: 1px solid #eee;">
        <button onclick="resetPasswordSubmit('${escapeHtml(u.username)}')" style="padding: 5px 10px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; margin-right: 4px;">Reset Password</button>
        ${deactivateBtn}
    </td>
</tr>`;
        }).join('');
        wrap.innerHTML = `
<table style="width: 100%; border-collapse: collapse;">
    <thead>
        <tr style="background: #f5f5f5;">
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

    async function createUserSubmit() {
        const username = document.getElementById('um-new-username').value.trim();
        const password = document.getElementById('um-new-password').value;
        const user_type = document.getElementById('um-new-type').value;
        const email = document.getElementById('um-new-email').value.trim() || null;
        if (!username || !password) {
            showStatus('Username and password are required.', 'error');
            return;
        }
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

    async function deactivateUserSubmit(username) {
        if (!confirm(`Deactivate user '${username}'? They will no longer be able to log in.`)) return;
        try {
            const resp = await fetch(`${API_BASE}/users/${encodeURIComponent(username)}`, {
                method: 'DELETE',
                headers: authHeaders()
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                showStatus(data.detail || `Failed to deactivate (${resp.status})`, 'error');
                return;
            }
            showStatus(`User '${username}' deactivated.`, 'success');
            loadUsers();
        } catch (e) {
            showStatus(`Error: ${e.message}`, 'error');
        }
    }

    function openUserManagement() {
        injectModal();
        const modal = document.getElementById('user-mgmt-modal');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        loadUsers();
    }

    function closeUserManagement() {
        const modal = document.getElementById('user-mgmt-modal');
        if (modal) modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    // Expose the handlers globally so inline onclick attrs can find them.
    window.openUserManagement = openUserManagement;
    window.closeUserManagement = closeUserManagement;
    window.createUserSubmit = createUserSubmit;
    window.changeUserTypeSubmit = changeUserTypeSubmit;
    window.resetPasswordSubmit = resetPasswordSubmit;
    window.deactivateUserSubmit = deactivateUserSubmit;
})();
