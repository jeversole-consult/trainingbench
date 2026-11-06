// TB-US-087: shared version-lifecycle helpers (release / promote / deprecate).
// Loaded on any page that renders action buttons for versioned components
// (adapters, training-sets, prompts, routes, rag, harness).
//
// Public API on window.tbLifecycle:
//   .badge(state)                       -> HTML string for a state badge
//   .controls(cfg)                      -> HTML string for action buttons + inline error slot
//   .act(component, versionId, action,  -> async fn invoked by the buttons
//        currentPromotedId, onDoneName)
//
// Caller contract for controls():
//   cfg.component     'adapter' | 'training-set' | 'prompt' | 'route' | 'rag' | 'harness'
//   cfg.versionId     numeric
//   cfg.state         'draft' | 'released' | 'promoted' | 'deprecated'
//   cfg.promotedId    currently-promoted version id for this component on this agent (nullable)
//   cfg.promotable    false for harness; otherwise true
//   cfg.onDoneName    name of a global (window.) function called after a successful transition

(function () {
    const STATE_STYLE = {
        draft:      { bg: '#fafafa', fg: '#777' },
        released:   { bg: '#e3f2fd', fg: '#1565c0' },
        promoted:   { bg: '#e8f5e9', fg: '#2e7d32' },
        deprecated: { bg: '#fff3e0', fg: '#8d6e63' },
    };

    function token() {
        return sessionStorage.getItem('session_token');
    }

    function badge(state) {
        const s = STATE_STYLE[state] || STATE_STYLE.draft;
        return `<span style="background:${s.bg}; color:${s.fg}; padding:2px 10px; border-radius:10px; font-size:0.85em; font-weight:600;">${state}</span>`;
    }

    function button(label, color, onClick) {
        return `<button onclick="${onClick}" style="padding:4px 10px; margin-right:6px; background:white; border:1px solid ${color}; color:${color}; border-radius:4px; cursor:pointer; font-size:0.85em; font-weight:500;" onmouseenter="this.style.background='${color}11'" onmouseleave="this.style.background='white'">${label}</button>`;
    }

    function controls(cfg) {
        const { component, versionId, state, promotedId, promotable, onDoneName } = cfg;
        const errorSlot = `<span id="tb-lc-err-${component}-${versionId}" style="color:#c33; font-size:0.85em; margin-left:8px; display:none;"></span>`;
        const btns = [];
        const promotedArg = promotedId === null || promotedId === undefined ? 'null' : promotedId;
        const act = (action, color, label) =>
            button(label, color, `tbLifecycle.act('${component}', ${versionId}, '${action}', ${promotedArg}, '${onDoneName}')`);
        if (state === 'draft') {
            btns.push(act('release', '#1565C0', 'Release'));
        }
        if (state === 'released' && promotable) {
            btns.push(act('promote', '#2E7D32', 'Promote'));
        }
        if (state !== 'deprecated') {
            btns.push(act('deprecate', '#8d6e63', 'Deprecate'));
        }
        return btns.join('') + errorSlot;
    }

    async function act(component, versionId, action, currentPromotedId, onDoneName) {
        if (action === 'promote' && currentPromotedId && currentPromotedId !== versionId) {
            if (!confirm(`Promote ${component} version #${versionId}?\n\nThis will deprecate the currently promoted version (#${currentPromotedId}).`)) {
                return;
            }
        }
        const errSlot = document.getElementById(`tb-lc-err-${component}-${versionId}`);
        if (errSlot) { errSlot.style.display = 'none'; errSlot.textContent = ''; }
        try {
            const res = await fetch(`/${component}-versions/${versionId}/${action}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token()}` },
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                throw new Error(body.detail || `${res.status} ${res.statusText}`);
            }
            if (onDoneName && typeof window[onDoneName] === 'function') {
                window[onDoneName]();
            }
        } catch (e) {
            if (errSlot) {
                errSlot.textContent = `${action} failed: ${e.message}`;
                errSlot.style.display = 'inline';
            } else {
                alert(`${action} failed: ${e.message}`);
            }
        }
    }

    window.tbLifecycle = { badge, controls, act };
})();
