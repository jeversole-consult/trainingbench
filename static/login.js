// API base URL - automatically detect and use current origin
const API_BASE = window.location.origin;

// Check gate token on page load
window.addEventListener('DOMContentLoaded', async function() {
    const gateToken = localStorage.getItem('gate_token');

    // If no gate token, redirect to gate page immediately
    if (!gateToken) {
        window.location.href = '/static/gate.html';
        return;
    }

    // Verify gate token with backend
    try {
        const response = await fetch(`${API_BASE}/auth/check-gate`, {
            headers: { 'X-Gate-Token': gateToken }
        });

        if (response.status === 404) {
            // Gate not enabled, proceed to login
            return;
        }

        if (!response.ok) {
            // Gate is enabled but token is invalid - redirect to gate
            localStorage.removeItem('gate_token');
            window.location.href = '/static/gate.html';
            return;
        }

        // Gate token is valid, allow login
    } catch (error) {
        console.error('Gate check failed:', error);
        // On error, redirect to gate for safety
        localStorage.removeItem('gate_token');
        window.location.href = '/static/gate.html';
    }
});

document.getElementById('login-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('login-btn');
    const errorMessage = document.getElementById('error-message');
    
    // Clear previous errors
    errorMessage.classList.remove('show');
    errorMessage.textContent = '';
    
    // Disable button
    loginBtn.disabled = true;
    loginBtn.textContent = 'Logging in...';
    
    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            }),
            credentials: 'include' // Include cookies
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Store session token (sessionStorage = per-tab isolation)
            if (data.session_token) {
                sessionStorage.setItem('session_token', data.session_token);
            }

            // Clear any stale training session data from localStorage
            localStorage.removeItem('training_session_state');
            localStorage.removeItem('training_session_name');
            localStorage.removeItem('training_session_count');
            localStorage.removeItem('completed_training_sessions');

            // TB-US-049: first-login forced password change
            if (data.must_change_password) {
                window.location.href = '/static/first-change-password.html';
                return;
            }

            // Redirect to main app
            window.location.href = '/static/index.html';
        } else {
            // Show error
            errorMessage.textContent = data.detail || 'Invalid credentials';
            errorMessage.classList.add('show');
            loginBtn.disabled = false;
            loginBtn.textContent = 'Login';
        }
    } catch (error) {
        errorMessage.textContent = 'Connection error. Please try again.';
        errorMessage.classList.add('show');
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
});

// Auto-focus username field
document.getElementById('username').focus();
