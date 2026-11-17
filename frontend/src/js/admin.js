
// =========================================
// WONKA ADMIN DASHBOARD
// =========================================

import { API_BASE_URL } from './api.js';

let csrfToken = null;

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

// Upload elements
const uploadForm = document.getElementById("upload-form");
const documentFile = document.getElementById("document-file");
const uploadButton = document.getElementById("upload-button");
const uploadProgressSection = document.getElementById("upload-progress-section");
const uploadProgress = document.getElementById("upload-progress");
const uploadPercentage = document.getElementById("upload-percentage");
const uploadStatus = document.getElementById("upload-status");
const uploadResult = document.getElementById("upload-result");


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


const MAX_UPLOAD_SIZE = 15 * 1024 * 1024;
const UPLOAD_SUCCESS_MESSAGE_DURATION = 2000;
let uploadResultTimeout = null;

const SUPPORTED_EXTENSIONS = [
    ".pdf",
    ".docx",
    ".txt",
    ".md"
];

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
    csrfToken = null;
    showLoginView();

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
        controller.abort();
    }, SESSION_TIMEOUT);

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/session`, {
            method: "GET",
            credentials: "include",
            signal: controller.signal
        });

        if (response.status === 401) {
            return false;
        }

        if (response.ok) {
            const data = await response.json();

            if (typeof data.csrf_token !== "string" || !data.csrf_token) {
                showLoginMessage(
                    "Unable to verify your security token. Please try again."
                );
                return false;
            }

            csrfToken = data.csrf_token;
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
    csrfToken = null;

    loginButton.disabled = true;
    loginButton.textContent = "Logging in...";

    const controller = new AbortController();

    const timeoutId = setTimeout(() => {
        controller.abort();
    }, SESSION_TIMEOUT);

    try {
        const response = await fetch(`${API_BASE_URL}/api/admin/login`, {
            method: "POST",
            credentials: "include",
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

        const data = await response.json();

        if (typeof data.csrf_token !== "string" || !data.csrf_token) {
            showLoginMessage(
                "Login response did not contain a security token. Please try again."
            );
            return;
        }

        csrfToken = data.csrf_token;
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





// =========================================
// ADMIN LOGOUT
// =========================================

logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = "Logging out...";

    try {
        if (!csrfToken) {
            throw new Error("CSRF token is missing.");
        }

        const response = await fetch(`${API_BASE_URL}/api/admin/logout`, {
            method: "POST",
            credentials: "include",
            headers: {
                "X-CSRF-Token": csrfToken
            }
        });

        if (!response.ok) {
            throw new Error(`Logout failed (HTTP ${response.status}).`);
        }

        csrfToken = null;

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








// =========================================
// DOCUMENT UPLOAD
// =========================================

uploadForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const file = documentFile.files[0];

    // Validate file selection
    if (!file) {
        showUploadResult("Please select a document.", false);
        return;
    }

    // Validate extension
    const extension = file.name
        .slice(file.name.lastIndexOf("."))
        .toLowerCase();

    if (!SUPPORTED_EXTENSIONS.includes(extension)) {
        showUploadResult(
            "Unsupported file format. Please select PDF, DOCX, TXT or MD.",
            false
        );
        return;
    }

    // Validate file size
    if (file.size > MAX_UPLOAD_SIZE) {
        showUploadResult(
            "File size exceeds the 15 MB upload limit.",
            false
        );
        return;
    }

    // Get CSRF token
    if (!csrfToken) {
        showUploadResult(
            "Your security token is missing. Please refresh the page and try again.",
            false
        );
        return;
    }

    // Prepare upload
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();

    uploadButton.disabled = true;
    documentFile.disabled = true;
    uploadButton.textContent = "Uploading...";

    clearUploadResultTimeout();
    uploadResult.hidden = true;
    uploadResult.textContent = "";

    uploadProgressSection.hidden = false;
    uploadProgress.value = 0;
    uploadPercentage.textContent = "0%";
    uploadStatus.textContent = "Uploading document...";

    // Track upload progress
    xhr.upload.addEventListener("progress", (event) => {
        if (!event.lengthComputable) return;

        const percentage = Math.round(
            (event.loaded / event.total) * 100
        );

        uploadProgress.value = percentage;
        uploadPercentage.textContent = `${percentage}%`;
    });

    // Upload completed; server is processing the document
    xhr.upload.addEventListener("load", () => {
        uploadStatus.textContent =
            "Document received. Processing and indexing...";
    });

    // Handle server response
    xhr.addEventListener("load", () => {
        let data = xhr.response;

        if (!data || typeof data !== "object") {
            try {
                data = JSON.parse(xhr.responseText);
            } catch {
                data = {};
            }
        }

        if (xhr.status >= 200 && xhr.status < 300) {
            uploadProgress.value = 100;
            uploadPercentage.textContent = "100%";

            showUploadResult(
                `Document uploaded successfully!\n\n` +
                `Filename: ${data.filename}\n` +
                `Chunks indexed: ${data.inserted_objects}`,
                true
            );

            uploadForm.reset();

        } else {
            const message =
                data.detail ||
                "Document upload failed. Please try again.";

            showUploadResult(message, false);
        }

        uploadProgressSection.hidden = true;
        uploadButton.disabled = false;
        documentFile.disabled = false;
        uploadButton.textContent = "Upload Document";
    });

    // Handle network errors
    xhr.addEventListener("error", () => {
        showUploadResult(
            "Unable to connect to the server. Please check your connection.",
            false
        );

        resetUploadControls();
    });

    xhr.addEventListener("abort", () => {
        showUploadResult(
            "The upload was cancelled.",
            false
        );

        resetUploadControls();
    });

    xhr.open("POST", `${API_BASE_URL}/api/admin/upload`);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-CSRF-Token", csrfToken);

    xhr.send(formData);
});


// =========================================
// UPLOAD RESULT HELPERS
// =========================================

function showUploadResult(message, success) {
    clearUploadResultTimeout();
    uploadResult.textContent = message;
    uploadResult.hidden = false;

    uploadResult.classList.remove(
        "border-red-200",
        "bg-red-50",
        "text-red-700",
        "border-green-200",
        "bg-green-50",
        "text-green-700"
    );

    uploadResult.classList.add(
        "border",
        success ? "border-green-200" : "border-red-200",
        success ? "bg-green-50" : "bg-red-50",
        success ? "text-green-700" : "text-red-700"
    );

    if (success) {
        const timeout = setTimeout(() => {
            if (uploadResultTimeout !== timeout) {
                return;
            }

            uploadResult.hidden = true;
            uploadResult.textContent = "";
            uploadResultTimeout = null;
        }, UPLOAD_SUCCESS_MESSAGE_DURATION);

        uploadResultTimeout = timeout;
    }
}


function clearUploadResultTimeout() {
    if (uploadResultTimeout !== null) {
        clearTimeout(uploadResultTimeout);
        uploadResultTimeout = null;
    }
}


function resetUploadControls() {
    uploadProgressSection.hidden = true;
    uploadButton.disabled = false;
    documentFile.disabled = false;
    uploadButton.textContent = "Upload Document";
}
