// Collapsible left-nav drawer — shared across index.html, training_sets.html, training_runs.html.
// TB-US-018 (2026-10-15): replaces the 9-tab horizontal bar on index.html + unifies
// navigation across the three main pages via a single hamburger-toggled drawer.
//
// Visual theming of the drawer (purple → amber) ships separately in TB-US-042.

(function () {
    const NAV_STORAGE_KEY = 'tb_nav_open';   // 'true' | 'false'
    const CURRENT_AGENT_STORAGE_KEY = 'tb_current_agent';  // TB-US-048 R17 (per-tab via sessionStorage)
    const API_BASE = window.location.origin;

    // Flat nav list. target='tab' → calls window.switchTab(id) on index.html,
    // or navigates to /static/index.html#id from the other pages.
    // target='page' → window.location.href = href.
    const NAV_ITEMS = [
        { id: 'upload',        label: 'Upload',         icon: '📤', target: 'tab'  },
        { id: 'scrape',        label: 'Scrape',         icon: '🕸️', target: 'tab'  },
        { id: 'chat',          label: 'Chat',           icon: '💬', target: 'tab'  },
        { id: 'powersearch',   label: 'PowerSearch',    icon: '⚡', target: 'tab'  },
        { id: 'compare',       label: 'Compare',        icon: '⚖️', target: 'tab'  },
        { id: 'search',        label: 'Search',         icon: '🔍', target: 'tab'  },
        { id: 'manage',        label: 'Documents',      icon: '📑', target: 'tab'  },
        { id: 'history',       label: 'Query History',  icon: '🕘', target: 'tab'  },
        { id: 'databases',     label: 'Databases',      icon: '🗄️', target: 'tab'  },
        { id: 'training_sets', label: 'Training Sets',  icon: '🎓', target: 'page', href: '/static/training_sets.html' },
        { id: 'training_runs', label: 'Training Runs',  icon: '🏃', target: 'page', href: '/static/training_runs.html' },
    ];

    function detectCurrentPage() {
        const path = window.location.pathname;
        if (path.endsWith('/training_sets.html')) return 'training_sets';
        if (path.endsWith('/training_runs.html')) return 'training_runs';
        return 'index';
    }

    function currentActiveItem() {
        const page = detectCurrentPage();
        if (page === 'training_sets') return 'training_sets';
        if (page === 'training_runs') return 'training_runs';
        // On index: find the active tab-content element and strip -tab suffix
        const activeTab = document.querySelector('.tab-content.active');
        if (activeTab) {
            const id = activeTab.id || '';
            return id.replace(/-tab$/, '');
        }
        return 'chat';  // TB-US-046: default landing tab
    }

    function reserveHamburgerSpace() {
        // The hamburger is fixed at top:12/left:12 and ~46px wide. Make sure the
        // page header has enough left padding so content doesn't underlap it.
        // Covers index.html, training_sets.html, training_runs.html uniformly.
        const header = document.querySelector('header');
        if (!header) return;
        const current = parseInt(window.getComputedStyle(header).paddingLeft, 10) || 0;
        if (current < 70) header.style.paddingLeft = '70px';
    }

    function injectNav() {
        if (document.getElementById('tb-left-nav')) return;

        reserveHamburgerSpace();

        // Hamburger button — fixed upper-left
        const hamburger = document.createElement('button');
        hamburger.id = 'tb-nav-hamburger';
        hamburger.setAttribute('aria-label', 'Open navigation menu');
        hamburger.innerHTML = '☰';
        hamburger.onclick = toggleNav;
        hamburger.style.cssText = [
            'position: fixed',
            'top: 12px',
            'left: 12px',
            'z-index: 2050',
            'background: rgba(255, 255, 255, 0.92)',
            'color: #333',
            'border: 1px solid #ccc',
            'border-radius: 4px',
            'padding: 4px 12px',
            'font-size: 1.5em',
            'line-height: 1.2',
            'cursor: pointer',
            'box-shadow: 0 1px 3px rgba(0,0,0,0.15)',
        ].join('; ');
        document.body.appendChild(hamburger);

        // Backdrop
        const backdrop = document.createElement('div');
        backdrop.id = 'tb-nav-backdrop';
        backdrop.onclick = closeNav;
        backdrop.style.cssText = [
            'position: fixed',
            'top: 0', 'left: 0',
            'width: 100%', 'height: 100%',
            'background: rgba(0, 0, 0, 0.3)',
            'z-index: 2040',
            'display: none',
        ].join('; ');
        document.body.appendChild(backdrop);

        // Drawer — flex-column so logout can pin to the bottom (TB-US-045 Tweak 8).
        const drawer = document.createElement('div');
        drawer.id = 'tb-left-nav';
        drawer.setAttribute('aria-label', 'Site navigation');
        drawer.style.cssText = [
            'position: fixed',
            'top: 0', 'left: 0',
            'width: 280px',
            'height: 100%',
            'background: #ffffff',
            'box-shadow: 2px 0 8px rgba(0, 0, 0, 0.18)',
            'z-index: 2060',
            'transform: translateX(-100%)',
            'transition: transform 200ms ease-out',
            'padding: 0',
            'overflow: hidden',
            'display: flex',
            'flex-direction: column',
            'box-sizing: border-box',
        ].join('; ');

        // TB-US-045 Tweak 7: in-drawer close button (back-arrow). Keep
        // existing close methods (Escape, backdrop click, item click)
        // but surface an explicit affordance so the drawer's collapse
        // control is obvious from inside the drawer.
        const headerHtml = `
<div class="tb-nav-header" style="padding: 12px 16px; border-bottom: 1px solid #E0E0E0; display: flex; align-items: center; justify-content: flex-start; margin-bottom: 8px;">
    <button onclick="window.__tbNavClose()" aria-label="Close navigation menu" title="Close menu (also: Esc or click outside)" style="background: none; border: 1px solid #E0E0E0; cursor: pointer; font-size: 1em; padding: 6px 12px; color: #333; border-radius: 4px; display: flex; align-items: center; gap: 6px; transition: background 100ms;" onmouseenter="this.style.background='rgba(0,0,0,0.04)'" onmouseleave="this.style.background='none'">
        <span style="font-size: 1.2em; line-height: 1;">←</span>
        <span>Close</span>
    </button>
</div>
<!-- TB-US-048: agent-selector widget (top of drawer, below Close) -->
<div id="tb-agent-selector" class="tb-agent-selector" style="padding: 10px 16px; background: rgba(204, 120, 92, 0.08); border-bottom: 1px solid #E0E0E0;">
    <div id="tb-agent-current" role="button" tabindex="0" onclick="window.__tbAgentDropdownToggle()" onkeydown="if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); window.__tbAgentDropdownToggle(); }" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; cursor: pointer; padding: 6px 10px; background: white; border: 1px solid #E0E0E0; border-radius: 6px; transition: border-color 100ms;" onmouseenter="this.style.borderColor='#CC785C'" onmouseleave="this.style.borderColor='#E0E0E0'" title="Switch agent">
        <span style="font-size: 0.9em; color: #333;">
            <span style="font-size: 1.1em;">🤖</span>
            <span style="color: #666;">Current agent:</span>
            <strong id="tb-agent-current-name" style="color: #CC785C;">—</strong>
        </span>
        <span id="tb-agent-dropdown-caret" style="color: #999; font-size: 0.8em;">▼</span>
    </div>
    <div id="tb-agent-dropdown" style="display: none; margin-top: 6px; background: white; border: 1px solid #E0E0E0; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); max-height: 240px; overflow-y: auto;">
        <!-- populated by refreshAgentSelector() -->
    </div>
</div>`;

        const activeId = currentActiveItem();
        // Scrollable nav-items region (flex-grow in the drawer column).
        const navItemsHtml = `<div class="tb-nav-items" style="flex: 1; overflow-y: auto; padding-bottom: 10px;">` +
            NAV_ITEMS.map(item => {
                const isActive = (item.id === activeId);
                const activeStyle = isActive
                    ? 'background: rgba(204, 120, 92, 0.1); border-left: 3px solid #CC785C; font-weight: bold; color: #333;'
                    : 'border-left: 3px solid transparent; color: #555;';
                return `<div class="tb-nav-item" data-id="${item.id}" data-target="${item.target}"${item.href ? ` data-href="${item.href}"` : ''} role="button" tabindex="0" style="padding: 12px 20px; cursor: pointer; display: flex; align-items: center; gap: 12px; font-size: 0.95em; transition: background 100ms; ${activeStyle}">
    <span style="font-size: 1.25em; flex-shrink: 0;">${item.icon}</span>
    <span>${item.label}</span>
</div>`;
            }).join('') +
            `</div>`;

        // TB-US-045 Tweak 8: Logout footer, bottom-pinned via flex-column.
        // Tweak 19 (2026-10-22): adds an Admin group above Logout for super
        // users. Starts the admin-tier drawer-footer surface — reshapes
        // TB-US-044 Q11 from "top-bar avatar menu" toward "drawer-footer
        // admin group". Hidden by default; script.js reveals it when a
        // super user is authenticated.
        const footerHtml = `
<div class="tb-nav-footer" style="flex-shrink: 0; border-top: 1px solid #E0E0E0; padding: 8px 0 0 0; background: #FAFAFA;">
    <!-- TB-US-045 Tweak 20: single Admin entry with a collapsible dropdown
         holding the admin-tier functions (Users, API Keys, …). Super-only. -->
    <div id="tb-nav-admin-group" style="display: none;">
        <div id="tb-nav-admin-trigger" role="button" tabindex="0" aria-expanded="false" onclick="window.__tbAdminDropdownToggle()" onkeydown="if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); window.__tbAdminDropdownToggle(); }" style="padding: 12px 20px; cursor: pointer; display: flex; align-items: center; gap: 12px; font-size: 0.95em; color: #555; border-left: 3px solid transparent; transition: background 100ms;" onmouseenter="this.style.background='rgba(0,0,0,0.04)'" onmouseleave="this.style.background=''" title="Administrative functions (super-only)">
            <span style="font-size: 1.25em; flex-shrink: 0;">⚙️</span>
            <span style="flex: 1;">Admin</span>
            <span id="tb-nav-admin-caret" style="color: #999; font-size: 0.8em;">▼</span>
        </div>
        <div id="tb-nav-admin-dropdown" style="display: none; background: #F5F5F5;">
            <div class="tb-nav-admin-subitem" role="button" tabindex="0" onclick="if (typeof window.openUserManagement === 'function') window.openUserManagement()" onkeydown="if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); if (typeof window.openUserManagement === 'function') window.openUserManagement(); }" style="padding: 10px 20px 10px 44px; cursor: pointer; display: flex; align-items: center; gap: 12px; font-size: 0.9em; color: #555; transition: background 100ms;" onmouseenter="this.style.background='rgba(0,0,0,0.04)'" onmouseleave="this.style.background=''" title="Manage TrainingBench users">
                <span style="font-size: 1.15em; flex-shrink: 0;">👥</span>
                <span>Users</span>
            </div>
            <div class="tb-nav-admin-subitem" role="button" tabindex="0" onclick="if (typeof window.openApiKeyManagement === 'function') window.openApiKeyManagement()" onkeydown="if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); if (typeof window.openApiKeyManagement === 'function') window.openApiKeyManagement(); }" style="padding: 10px 20px 10px 44px; cursor: pointer; display: flex; align-items: center; gap: 12px; font-size: 0.9em; color: #555; transition: background 100ms;" onmouseenter="this.style.background='rgba(0,0,0,0.04)'" onmouseleave="this.style.background=''" title="Manage API keys">
                <span style="font-size: 1.15em; flex-shrink: 0;">🔑</span>
                <span>API Keys</span>
            </div>
        </div>
    </div>
    <div class="tb-nav-logout" role="button" tabindex="0" onclick="window.__tbNavLogout()" onkeydown="if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); window.__tbNavLogout(); }" style="padding: 12px 20px; cursor: pointer; display: flex; align-items: center; gap: 12px; font-size: 0.95em; color: #555; border-left: 3px solid transparent; transition: background 100ms;" onmouseenter="this.style.background='rgba(0,0,0,0.04)'" onmouseleave="this.style.background=''" title="Sign out of TrainingBench">
        <span style="font-size: 1.25em; flex-shrink: 0;">🚪</span>
        <span>Logout</span>
    </div>
</div>`;

        drawer.innerHTML = headerHtml + navItemsHtml + footerHtml;
        document.body.appendChild(drawer);

        // Wire item click + keyboard
        drawer.querySelectorAll('.tb-nav-item').forEach(el => {
            const handler = () => {
                const id = el.getAttribute('data-id');
                const target = el.getAttribute('data-target');
                const href = el.getAttribute('data-href');
                handleItemClick(id, target, href);
            };
            el.addEventListener('click', handler);
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); }
            });
            // Hover affordance (non-active rows)
            el.addEventListener('mouseenter', () => {
                if (el.getAttribute('data-id') !== currentActiveItem()) {
                    el.style.background = 'rgba(0,0,0,0.04)';
                }
            });
            el.addEventListener('mouseleave', () => {
                if (el.getAttribute('data-id') !== currentActiveItem()) {
                    el.style.background = '';
                }
            });
        });

        // Escape closes drawer
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const d = document.getElementById('tb-left-nav');
                if (d && d.dataset.open === '1') closeNav();
            }
        });

        // Restore persisted state (default: closed on first visit)
        const persisted = localStorage.getItem(NAV_STORAGE_KEY);
        if (persisted === 'true') {
            openNav({ persist: false });
        }

        // TB-US-048: load the agent-selector list on drawer injection.
        refreshAgentSelector();

        // Hash routing — if we land on index.html with #tabname, switch to it
        if (detectCurrentPage() === 'index' && window.location.hash) {
            const tabId = window.location.hash.replace(/^#/, '');
            if (tabId && typeof window.switchTab === 'function') {
                // Defer to let the page's own init run first
                setTimeout(() => {
                    try { window.switchTab(tabId); refreshActive(tabId); } catch (e) {}
                }, 0);
            }
        }
    }

    function handleItemClick(id, target, href) {
        if (target === 'page') {
            window.location.href = href;
            return;
        }
        if (target === 'tab') {
            const page = detectCurrentPage();
            if (page !== 'index') {
                // Navigate to index.html with the chosen tab as hash
                window.location.href = '/static/index.html#' + encodeURIComponent(id);
                return;
            }
            if (typeof window.switchTab === 'function') {
                try { window.switchTab(id); } catch (e) { console.error('switchTab failed', e); }
            }
            refreshActive(id);
            closeNav();  // R3: collapse on click
        }
    }

    function refreshActive(activeId) {
        document.querySelectorAll('.tb-nav-item').forEach(el => {
            const id = el.getAttribute('data-id');
            if (id === activeId) {
                el.style.background = 'rgba(204, 120, 92, 0.1)';
                el.style.borderLeft = '3px solid #CC785C';
                el.style.fontWeight = 'bold';
                el.style.color = '#333';
            } else {
                el.style.background = '';
                el.style.borderLeft = '3px solid transparent';
                el.style.fontWeight = '';
                el.style.color = '#555';
            }
        });
    }

    function openNav(opts) {
        const drawer = document.getElementById('tb-left-nav');
        const backdrop = document.getElementById('tb-nav-backdrop');
        if (drawer) {
            drawer.style.transform = 'translateX(0)';
            drawer.dataset.open = '1';
        }
        if (backdrop) backdrop.style.display = 'block';
        if (!opts || opts.persist !== false) {
            localStorage.setItem(NAV_STORAGE_KEY, 'true');
        }
    }

    function closeNav() {
        const drawer = document.getElementById('tb-left-nav');
        const backdrop = document.getElementById('tb-nav-backdrop');
        if (drawer) {
            drawer.style.transform = 'translateX(-100%)';
            drawer.dataset.open = '0';
        }
        if (backdrop) backdrop.style.display = 'none';
        localStorage.setItem(NAV_STORAGE_KEY, 'false');
        // TB-US-045 Tweak 22: reset any expanded in-drawer dropdowns so the
        // drawer re-opens in a clean state.
        _collapseDrawerDropdowns();
    }

    function _collapseDrawerDropdowns() {
        // Agent selector (top of drawer)
        const agentDd = document.getElementById('tb-agent-dropdown');
        const agentCaret = document.getElementById('tb-agent-dropdown-caret');
        if (agentDd) agentDd.style.display = 'none';
        if (agentCaret) agentCaret.textContent = '▼';
        // Admin group (drawer footer)
        const adminDd = document.getElementById('tb-nav-admin-dropdown');
        const adminCaret = document.getElementById('tb-nav-admin-caret');
        const adminTrigger = document.getElementById('tb-nav-admin-trigger');
        if (adminDd) adminDd.style.display = 'none';
        if (adminCaret) adminCaret.textContent = '▼';
        if (adminTrigger) adminTrigger.setAttribute('aria-expanded', 'false');
    }

    function toggleNav() {
        const drawer = document.getElementById('tb-left-nav');
        if (!drawer) return;
        if (drawer.dataset.open === '1') closeNav(); else openNav();
    }

    // ------------------------------------------------------------------ //
    // TB-US-048: agent-selector widget
    // ------------------------------------------------------------------ //

    function getCurrentAgentName() {
        // sessionStorage = per-tab (TB-US-048 R18: tabs independent).
        return sessionStorage.getItem(CURRENT_AGENT_STORAGE_KEY) || 'default';
    }

    function setCurrentAgentName(name) {
        sessionStorage.setItem(CURRENT_AGENT_STORAGE_KEY, name);
    }

    function updateCurrentAgentLabel(name) {
        const label = document.getElementById('tb-agent-current-name');
        if (label) label.textContent = name || '—';
    }

    async function refreshAgentSelector() {
        const dropdown = document.getElementById('tb-agent-dropdown');
        if (!dropdown) return;
        updateCurrentAgentLabel(getCurrentAgentName());

        const token = sessionStorage.getItem('session_token');
        if (!token) {
            dropdown.innerHTML = '<div style="padding: 10px; color: #999; font-size: 0.85em;">Not authenticated</div>';
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/agents?include_retired=false`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
            const data = await res.json();
            const agents = (data.agents || []).filter(a => a.state === 'active');

            // If the stored current agent no longer exists in the active list,
            // fall back to the first active agent (likely 'default').
            const currentName = getCurrentAgentName();
            const stillValid = agents.find(a => a.name === currentName);
            if (!stillValid && agents.length) {
                setCurrentAgentName(agents[0].name);
                updateCurrentAgentLabel(agents[0].name);
            }

            const effectiveCurrent = getCurrentAgentName();
            const itemsHtml = agents.map(a => {
                const isCurrent = (a.name === effectiveCurrent);
                const style = isCurrent
                    ? 'padding: 8px 12px; cursor: pointer; background: rgba(204, 120, 92, 0.1); font-weight: 600;'
                    : 'padding: 8px 12px; cursor: pointer;';
                const check = isCurrent ? '<span style="color: #CC785C; margin-right: 6px;">●</span>' : '<span style="margin-right: 6px; opacity: 0;">●</span>';
                return `<div class="tb-agent-dd-item" data-name="${escapeAttr(a.name)}" role="button" tabindex="0" style="${style}" onmouseenter="this.style.background='rgba(0,0,0,0.04)'" onmouseleave="this.style.background='${isCurrent ? 'rgba(204, 120, 92, 0.1)' : ''}'">${check}<span style="font-family: monospace; font-size: 0.9em;">${escapeHtml(a.name)}</span>${a.display_name && a.display_name !== a.name ? ` <span style="color: #999; font-size: 0.85em;">— ${escapeHtml(a.display_name)}</span>` : ''}</div>`;
            }).join('');

            const manageHtml = `
<div style="border-top: 1px solid #E0E0E0; padding: 8px 12px; font-size: 0.85em;">
    <a href="#" onclick="event.preventDefault(); window.__tbAgentOpenMgmt();" style="color: #CC785C; text-decoration: none;">Manage agents →</a>
</div>`;

            dropdown.innerHTML = itemsHtml + manageHtml;

            dropdown.querySelectorAll('.tb-agent-dd-item').forEach(el => {
                const handler = () => {
                    const name = el.getAttribute('data-name');
                    switchAgent(name);
                };
                el.addEventListener('click', handler);
                el.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handler(); }
                });
            });
        } catch (e) {
            dropdown.innerHTML = `<div style="padding: 10px; color: #c33; font-size: 0.85em;">Failed to load: ${escapeHtml(e.message)}</div>`;
        }
    }

    function toggleAgentDropdown() {
        const dropdown = document.getElementById('tb-agent-dropdown');
        const caret = document.getElementById('tb-agent-dropdown-caret');
        if (!dropdown) return;
        const open = dropdown.style.display === 'block';
        dropdown.style.display = open ? 'none' : 'block';
        if (caret) caret.textContent = open ? '▼' : '▲';
    }

    function switchAgent(name) {
        setCurrentAgentName(name);
        updateCurrentAgentLabel(name);
        // Close the dropdown but keep drawer open per TB-US-048 R17.
        const dropdown = document.getElementById('tb-agent-dropdown');
        if (dropdown) dropdown.style.display = 'none';
        const caret = document.getElementById('tb-agent-dropdown-caret');
        if (caret) caret.textContent = '▼';
        refreshAgentSelector();  // re-render with the new current highlight
        // Notify other UI components (chat/upload/etc.) that the agent changed.
        document.dispatchEvent(new CustomEvent('tb:agent-changed', { detail: { name } }));
    }

    function openAgentManagement() {
        // Close dropdown first so the modal is unobstructed.
        const dropdown = document.getElementById('tb-agent-dropdown');
        if (dropdown) dropdown.style.display = 'none';
        if (typeof window.openAgentManagement === 'function') {
            window.openAgentManagement();
        } else {
            console.warn('[TB-US-048] agent_management.js not loaded on this page');
        }
    }

    function escapeHtml(s) {
        return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
    }

    function escapeAttr(s) {
        return String(s || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
    }

    // Public hooks
    window.__tbAgentDropdownToggle = toggleAgentDropdown;
    window.__tbAgentOpenMgmt = openAgentManagement;
    window.__tbRefreshAgentSelector = refreshAgentSelector;
    window.__tbCurrentAgent = getCurrentAgentName;

    // TB-US-045 Tweak 20: toggle the admin-dropdown (collapsible group
    // holding Users, API Keys, …).
    window.__tbAdminDropdownToggle = function () {
        const dropdown = document.getElementById('tb-nav-admin-dropdown');
        const caret = document.getElementById('tb-nav-admin-caret');
        const trigger = document.getElementById('tb-nav-admin-trigger');
        if (!dropdown) return;
        const open = dropdown.style.display === 'block';
        dropdown.style.display = open ? 'none' : 'block';
        if (caret) caret.textContent = open ? '▼' : '▲';
        if (trigger) trigger.setAttribute('aria-expanded', open ? 'false' : 'true');
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectNav);
    } else {
        injectNav();
    }

    // Expose for script.js integration: when switchTab is called elsewhere,
    // this lets index.html keep the drawer's active indicator in sync.
    window.__tbNavRefreshActive = refreshActive;
    // TB-US-045 Tweak 7: expose closeNav for in-drawer close button.
    window.__tbNavClose = closeNav;
    // TB-US-045 Tweak 8: wrapper that calls each page's logout() definition.
    // Falls back to a minimal cleanup if the page didn't define one.
    window.__tbNavLogout = function () {
        if (typeof window.logout === 'function') {
            window.logout();
            return;
        }
        // Fallback: clear tokens + go to login
        try {
            sessionStorage.removeItem('session_token');
            localStorage.removeItem('gate_token');
        } catch (e) {}
        window.location.href = '/static/login.html';
    };
})();
