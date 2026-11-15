
// =========================================
// WONKA ADMIN DASHBOARD
// =========================================

// Login elements
const loginSection = document.getElementById("login-section");
const loginForm = document.getElementById("login-form");
const loginButton = document.getElementById("login-button");
const loginResult = document.getElementById("login-result");

// Dashboard elements
const adminHeader = document.getElementById("admin-header");
const welcomeSection = document.getElementById("welcome-section");
const uploadSection = document.getElementById("upload-section");
const uploadGuidelines = document.getElementById("upload-guidelines");
const logoutButton = document.getElementById("logout-button");

// =========================================
// VIEW MANAGEMENT
// =========================================

function showLoginView() {
    loginSection.hidden = false;
    loginResult.hidden = true;
    loginResult.textContent = "";

    adminHeader.hidden = true;
    welcomeSection.hidden = true;
    uploadSection.hidden = true;
    uploadGuidelines.hidden = true;
}

function showDashboardView() {
    loginSection.hidden = true;

    adminHeader.hidden = false;
    welcomeSection.hidden = false;
    uploadSection.hidden = false;
    uploadGuidelines.hidden = false;
}



// =========================================
// SESSION MANAGEMENT
// =========================================

const SESSION_TIMEOUT = 15000;
const LOGIN_MESSAGE_DURATION = 2000;
let loginMessageTimeout = null;

function clearLoginMessageTimeout() {
    if (loginMessageTimeout !== null) {
        clearTimeout(loginMessageTimeout);
        loginMessageTimeout = null;
    }
}

function clearLoginMessage() {
    clearLoginMessageTimeout();
    loginResult.hidden = true;
    loginResult.textContent = "";
}

function showLoginMessage(message) {
    clearLoginMessageTimeout();
    loginResult.textContent = message;
    loginResult.hidden = false;

    loginResult.classList.remove(
        "border-green-200",
        "bg-green-50",
        "text-green-700"
    );

    loginResult.classList.add(
        "border",
        "border-red-200",
        "bg-red-50",
        "text-red-700"
    );

    const timeout = setTimeout(() => {
        if (loginMessageTimeout !== timeout) {
            return;
        }

        loginResult.hidden = true;
        loginResult.textContent = "";
        loginMessageTimeout = null;
    }, LOGIN_MESSAGE_DURATION);

    loginMessageTimeout = timeout;
}






async function checkAdminSession() {
    showLoginView();

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
        controller.abort();
    }, SESSION_TIMEOUT);

    try {
        const response = await fetch("/api/admin/session", {
            method: "GET",
            credentials: "same-origin",
            signal: controller.signal
        });

        if (response.status === 401) {
            return false;
        }

        if (response.ok) {
            showDashboardView();
            return true;
        }

        showLoginMessage(
            `Unable to verify your session (HTTP ${response.status}). Please try again.`
        );

        return false;

    } catch (error) {
        if (error.name === "AbortError") {
            showLoginMessage(
                "Session check timed out. Please try again."
            );
        } else {
            showLoginMessage(
                "Unable to connect to the server. Please check your connection."
            );
        }

        return false;

    } finally {
        clearTimeout(timeoutId);
    }
}



// =========================================
// ADMIN LOGIN
// =========================================

function showLoginSuccess(message) {
    clearLoginMessageTimeout();
    loginResult.textContent = message;
    loginResult.hidden = false;

    loginResult.classList.remove(
        "border-red-200",
        "bg-red-50",
        "text-red-700"
    );

    loginResult.classList.add(
        "border",
        "border-green-200",
        "bg-green-50",
        "text-green-700"
    );
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document
        .getElementById("admin-username")
        .value.trim();

    const password = document
        .getElementById("admin-password")
        .value;

    clearLoginMessage();

    loginButton.disabled = true;
    loginButton.textContent = "Logging in...";

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
        controller.abort();
    }, SESSION_TIMEOUT);

    try {
        const response = await fetch("/api/admin/login", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username,
                password
            }),
            signal: controller.signal
        });

        if (response.status === 401) {
            showLoginMessage(
                "Invalid username or password. Please try again."
            );
            return;
        }

        if (!response.ok) {
            showLoginMessage(
                response.status >= 500
                    ? "The server is temporarily unavailable. Please try again later."
                    : `Login failed (HTTP ${response.status}). Please try again.`
            );
            return;
        }

        showLoginSuccess("Login successful! Verifying your session...");

        await new Promise(resolve => setTimeout(resolve, 800));

        const authenticated = await checkAdminSession();

        if (!authenticated && loginResult.hidden) {
            showLoginMessage(
                "Login succeeded, but your session could not be verified. Please try again."
            );
        }

    } catch (error) {
        if (error.name === "AbortError") {
            showLoginMessage(
                "Login request timed out. Please try again."
            );
        } else {
            showLoginMessage(
                "Unable to connect to the server. Please check your connection."
            );
        }

    } finally {
        clearTimeout(timeoutId);

        loginButton.disabled = false;
        loginButton.textContent = "Sign In";
    }
});

checkAdminSession();





function getCookie(name) {
    const cookie = document.cookie
        .split("; ")
        .find(row => row.startsWith(`${name}=`));

    return cookie ? cookie.split("=")[1] : null;
}

// =========================================
// ADMIN LOGOUT
// =========================================

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = "Logging out...";

    try {
        const csrfToken = getCookie("csrf_token");

        if (!csrfToken) {
            throw new Error("CSRF token is missing.");
        }

        const response = await fetch("/api/admin/logout", {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "X-CSRF-Token": csrfToken
            }
        });

        if (!response.ok) {
            throw new Error(`Logout failed (HTTP ${response.status}).`);
        }

        // Clear the password field
        document.getElementById("admin-password").value = "";

        showLoginView();
        const logoutSuccessMessage = "You have been logged out successfully.";
        showLoginSuccess(logoutSuccessMessage);

        setTimeout(() => {
            if (loginResult.textContent === logoutSuccessMessage) {
                loginResult.hidden = true;
                loginResult.textContent = "";
            }
        }, LOGIN_MESSAGE_DURATION);

    } catch (error) {
        console.error("Logout error:", error);
        alert("Unable to log out. Please try again.");

    } finally {
        logoutButton.disabled = false;
        logoutButton.textContent = "Logout";
    }
});
