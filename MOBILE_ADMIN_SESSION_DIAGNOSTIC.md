# Mobile Admin Session Diagnostic

## Executive summary

The source code implements the expected credentialed-cookie flow: the frontend uses `credentials: "include"` for admin login, session verification, and logout; production cookies are configured `SameSite=None; Secure`; and FastAPI CORS enables credentials for an explicit origin list.

The **most likely cause** of a mobile-only failure is that the Render frontend and Railway API are cross-site when accessed through their provider hostnames. In that case the admin session cookie is a third-party cookie in the frontend's `fetch()` context. `SameSite=None; Secure` permits cross-site cookie use under cookie rules, but it does not override browser-level third-party-cookie blocking. Safari/WebKit blocks cross-site cookies by default; Chromium behavior depends on version, settings, and policy. A login response can therefore return success and its JSON CSRF token while the browser declines to store or send `admin_session`; the following session request then receives HTTP 401.

This is a high-likelihood diagnosis, **not proven for the affected production session**. The repository does not contain the deployed `FRONTEND_ORIGINS` or `VITE_API_BASE_URL` values, actual public hostnames, a mobile network trace, or production request logs. Those must be checked to distinguish cookie blocking from a hostname/CORS or deployment configuration mismatch.

No source or authentication changes were made. This report does not include credentials, tokens, cookies, private keys, or live environment values.

## Relevant files and functions inspected

- [`backend/app/api/admin_routes.py`](backend/app/api/admin_routes.py#L42): `_auth_cookie_options()`, `admin_login()`, `admin_logout()`, and `admin_session()`.
- [`backend/app/security/authentication.py`](backend/app/security/authentication.py#L103): `create_admin_session()` and Firebase credential verification.
- [`backend/app/security/dependencies.py`](backend/app/security/dependencies.py#L8): `get_current_admin()`.
- [`backend/app/main.py`](backend/app/main.py#L43): FastAPI CORS middleware and origin list.
- [`backend/app/security/csrf.py`](backend/app/security/csrf.py#L13): origin and CSRF-cookie/header validation.
- [`frontend/src/js/admin.js`](frontend/src/js/admin.js#L129): `checkAdminSession()`, login, logout, and upload requests.
- [`frontend/src/js/api.js`](frontend/src/js/api.js#L1): shared `API_BASE_URL` constant.
- [`frontend/.env.example`](frontend/.env.example#L1), [`.env.example`](.env.example#L1): deployment configuration variable names and explanatory comments only; actual runtime values were not inspected.
- [`frontend/vite.config.mjs`](frontend/vite.config.mjs#L14): development-only `/api` proxy.
- [`backend/tests/test_admin_routes.py`](backend/tests/test_admin_routes.py#L11), [`backend/tests/test_auth_dependencies.py`](backend/tests/test_auth_dependencies.py#L10): route and dependency test coverage.

## Current backend cookie configuration

`_auth_cookie_options()` in [`admin_routes.py:42-52`](backend/app/api/admin_routes.py#L42) selects attributes according to `ENVIRONMENT`:

| Attribute | Current behavior |
|---|---|
| `HttpOnly` | `admin_session` is `HttpOnly`; `csrf_token` is intentionally not. Login, session refresh, and logout set/delete each with that distinction (`admin_routes.py:79-93`, `223-233`, `249-254`). |
| `Secure` | Enabled unless the environment is explicitly configured as development. The function defaults to production behavior if the variable is absent. |
| `SameSite` | `None` outside development; `Lax` in development. Production `None` is required for a cross-site fetch cookie, and is paired with `Secure`. |
| `Path` | `/` for both cookies. |
| `Domain` | Not supplied. The cookies are host-only cookies for the API host that returned them. They do not need to be shared with the Render host: the browser should send them to the Railway API host on later requests, if the browser permits the cross-site cookie. |
| `Max-Age` / `Expires` | Not supplied when cookies are created, so the browser treats them as session cookies. The Firebase session cookie itself is created with an eight-hour validity (`authentication.py:103-115`). Browser-session lifetime and server-side Firebase validity are therefore different limits. This is not, by itself, an explanation for immediate verification failure. |

`admin_login()` sets the Firebase cookie and a readable CSRF cookie (`admin_routes.py:63-95`). `admin_session()` validates the Firebase cookie first, then creates a CSRF cookie if one is absent (`admin_routes.py:239-257`). `admin_logout()` deletes both cookies using the same path/security/SameSite options and omits `Domain`, matching the host-only cookie scope (`admin_routes.py:218-235`).

## Current frontend request configuration

The admin calls are direct `fetch()` requests; there is no shared fetch wrapper or request interceptor that changes their options. [`api.js:1-2`](frontend/src/js/api.js#L1) provides only a base URL, taken from the build-time `VITE_API_BASE_URL` value or the empty string.

- Login: `POST /api/admin/login` includes `credentials: "include"` and JSON content type (`admin.js:214-293`, especially `238-249`).
- Session verification: `GET /api/admin/session` includes `credentials: "include"` (`admin.js:129-180`, especially `140-151`). On success it reads the CSRF token from JSON; on 401 it returns unauthenticated (`admin.js:146-162`).
- Logout: `POST /api/admin/logout` includes `credentials: "include"` and `X-CSRF-Token` (`admin.js:321-356`, especially `327-334`).
- Upload: the XHR sets `withCredentials = true` and the CSRF header (`admin.js:513-515`).

This is the correct frontend credential mode for cross-origin cookie requests. It also permits the browser to process `Set-Cookie` on a credentialed CORS response. It cannot force a browser to accept a cookie blocked by its privacy policy.

The login UI reports success from the login response and then waits 800 ms before calling `checkAdminSession()` (`admin.js:277-281`). Thus “login successful” does not establish that the browser stored the session cookie; the session check is the first source-level confirmation that the cookie returned to the backend.

The frontend environment example says the backend URL must be configured for deployment, whereas the Vite proxy in `vite.config.mjs:14-21` is only a development server proxy. If the deployed base URL is empty, the browser sends `/api/admin/...` to the frontend origin rather than the Railway API. The actual Render build setting was not inspected.

## Current CORS configuration

[`main.py:43-56`](backend/app/main.py#L43) builds `allow_origins` from the comma-separated `FRONTEND_ORIGINS` variable and enables:

- `allow_credentials=True`
- Methods `GET` and `POST`
- Headers `Content-Type` and `X-CSRF-Token`

There is no wildcard origin. This is compatible with credentialed CORS **only if** each browser `Origin` exactly matches an allowed origin, including scheme, hostname, and port, with no path or trailing slash. The example configuration is blank and documents that exact origins should be supplied; deployed values are unavailable here.

The login's JSON content type and the logout/upload custom CSRF header can trigger CORS preflight. The configured methods and headers cover the methods and custom headers used in these requests; the FastAPI CORS middleware handles preflight requests. A mismatch in the allowed origin can prevent the frontend from reading the response, and may prevent the preflighted login request from being sent.

The CSRF origin check separately performs exact string matching against the same environment variable (`csrf.py:13-28`). Logout additionally requires both the CSRF cookie and matching `X-CSRF-Token` header (`csrf.py:30-44`).

## Session verification behavior

`get_current_admin()` extracts `admin_session` from the incoming request (`dependencies.py:8-18`). If absent, it returns HTTP 401 with “Authentication required.” If present, it calls Firebase Admin `auth.verify_session_cookie(..., check_revoked=True)` (`dependencies.py:21-26`). An invalid/expired cookie returns HTTP 401 with a different detail; Firebase and other verification exceptions return HTTP 503 (`dependencies.py:28-45`).

The missing-cookie and invalid-cookie cases are distinguishable in the HTTP response body, but the frontend treats both 401 responses identically and does not display the response detail (`admin.js:146-147`). The dependency does not log whether the cookie was absent or verification failed, nor does it log the Firebase exception. Consequently, ordinary application logs may show a 401/503 access status but cannot establish whether the mobile browser sent the cookie. Do not log cookie values; safe diagnostic logging would record presence/verification outcome only.

## Complete authentication flow

1. The admin submits credentials in the frontend login form (`admin.js:214-249`).
2. The browser sends the credentialed POST to the origin selected by `API_BASE_URL`.
3. FastAPI calls `verify_admin_credentials()`, which authenticates through Firebase Authentication (`authentication.py`, credential verification implementation).
4. The backend exchanges the Firebase ID token for a Firebase session cookie with eight-hour validity (`authentication.py:103-115`).
5. The backend returns `admin_session` as `HttpOnly` and `csrf_token` as readable cookies, with production cross-site attributes (`admin_routes.py:79-93`). The response also contains the CSRF token in JSON.
6. The browser decides whether to store both cookies. `credentials: "include"` and CORS credentials allow this, but third-party cookie policy can still reject or partition storage.
7. After an 800 ms delay, frontend code sends `GET /api/admin/session` with credentials included (`admin.js:277-281`, `140-151`).
8. If accepted, the browser sends the API-host cookie in the request's `Cookie` header. JavaScript cannot directly read the `HttpOnly` session cookie.
9. FastAPI extracts and verifies `admin_session`. Missing cookies produce 401; Firebase verification failures produce 401 or 503 (`dependencies.py:13-45`).
10. Only an HTTP 200 response with a valid JSON CSRF token transitions the UI to the dashboard (`admin.js:153-162`).

**Most likely break point:** step 6 or 8. The login endpoint can return HTTP 200 and a JSON token, while the browser declines the cross-site `admin_session` cookie. Step 9 then sees no cookie and responds 401. If the cookie is present but Firebase verification returns 503, investigate backend/Firebase availability rather than cookie policy.

## Desktop vs. mobile compatibility analysis

### Confirmed from source

- Production cookie attributes are suitable for cross-site cookie use at the HTTP-cookie level: `SameSite=None` and `Secure`.
- Frontend requests use credential inclusion, and CORS allows credentials with a configured explicit allowlist.
- Cookies are scoped to the API host, not the frontend host. That is normal for an API cookie and is not an error by itself.
- The front- and backend origins are independently configurable. The repository does not confirm their live values or whether the mobile URL is identical to the desktop URL.

### Potential compatibility issue

When default Render and Railway hostnames are used, the frontend and API are on different sites. The API cookie is then third-party in a frontend-initiated cross-site request. Safari/WebKit's documented policy blocks cross-site cookies by default. Chrome/Android behavior is not uniform: third-party cookies may be restricted by browser version, user settings, developer flags, or enterprise policy. Desktop Chrome success therefore does not predict Safari/iOS or every Android Chrome configuration. Chrome on iOS uses WebKit, not the Android Chromium engine.

`SameSite=None; Secure` is necessary for the cookie to be eligible in a cross-site request, but it is not a third-party-cookie policy exemption. A custom-domain arrangement could change this: sibling frontend/API subdomains can remain cross-origin for CORS while being same-site if they share the same scheme and registrable domain. The actual deployed hostnames were not inspected, so the production site relationship remains unconfirmed.

### Other compatibility/configuration checks

- **HTTPS:** A production `Secure` cookie requires HTTPS. Provider-hosted production sites are typically HTTPS, but the actual URL and any redirects must be verified.
- **Hostname/redirect consistency:** Because `Domain` is omitted, the cookie belongs only to the API hostname that sent it. A redirect to a different API hostname or a frontend base URL that changes between requests can make it unavailable.
- **Origin mismatch:** A mobile user may enter a different frontend alias (for example, a custom domain versus a provider hostname). CORS and CSRF compare exact origins; each real frontend origin must be configured.
- **Private browsing/privacy settings:** These can block or partition cross-site state even when the same browser works in a regular desktop profile.
- **Session lifetime:** The browser cookie has no explicit `Max-Age`/`Expires`, while Firebase's server-side cookie is valid for eight hours. This may affect browser-restored sessions, but is a lower-likelihood explanation for a failure immediately after login.
- **Redirects:** No application-level redirect in the inspected auth requests was found. Whether the deployed API URL redirects at the proxy/hosting layer is not verifiable from repository source.

## Identified issues ranked by likelihood

### 1. Cross-site cookie blocked on mobile — highest likelihood, unconfirmed at runtime

The described Render-to-Railway setup normally uses separate sites. Safari blocks third-party cookies by default, and Chromium restrictions depend on the device's policy/settings. This symptom pattern—login endpoint success followed by session verification failure—matches the browser not storing or sending `admin_session`.

### 2. Production origins or API base URL differ from the expected deployment — possible, unconfirmed

The allowed origins and API base URL are deployment settings, not hard-coded values. A stale/incorrect `FRONTEND_ORIGINS` entry can cause CORS failure; an unset/wrong `VITE_API_BASE_URL` can target the frontend host instead of the API. A CORS failure on login normally prevents a successful frontend login response, so it is less consistent with the stated sequence than cookie blocking, but still must be ruled out.

### 3. Production environment selects development cookie settings — possible, lower likelihood

If the backend runtime is explicitly marked development, it sets `SameSite=Lax` and omits `Secure`. That would not work for the described HTTPS cross-site flow. The source defaults to production behavior, but the live environment setting was not read.

### 4. API/Firebase verification error after cookie delivery — possible, lower likelihood

If the session request includes the cookie but returns 503, Firebase verification or backend availability is implicated. If the cookie is present and returns 401, investigate expiration, revocation, malformed/rotated cookie, or Firebase project/configuration mismatch. No such production response or log evidence was provided.

### Confirmed implementation caveats, not likely immediate causes

- Cookies are browser-session cookies, despite the Firebase cookie's eight-hour validity.
- The verification dependency does not log missing versus invalid cookie outcomes; only response detail distinguishes those 401 cases.
- Existing login route tests assert cookie values but do not assert cookie attributes or exercise credentialed CORS in the standalone test app (`test_admin_routes.py:11-52`). They therefore do not validate browser cookie acceptance.

## Recommended minimal fixes (do not apply before reviewing)

1. **First diagnose, then prefer same-site delivery if third-party blocking is confirmed.** Serve the API through the frontend origin (same-origin reverse proxy) or use frontend/API custom domains under the same registrable domain. This avoids dependence on third-party cookie availability while retaining HTTPS. Merely changing to `SameSite=None` is not sufficient; the source already does that in production.
2. Verify the Render build's backend base URL is the canonical HTTPS API origin, and verify Railway's allowed-origin list contains the exact browser-visible frontend origin(s), without paths or trailing slashes. Check every alias used by desktop and mobile.
3. Verify the backend is running with production cookie settings. Keep `Secure` enabled for HTTPS production; do not make a production cookie insecure as a workaround.
4. Add privacy-safe diagnostic logging for session verification outcomes (cookie present/missing, Firebase verification success/failure category, response status), without logging cookie contents or tokens.
5. Consider an explicit browser-cookie lifetime only if the product intends sessions to survive browser restarts; align it intentionally with the Firebase server-side expiry. This is not the first fix to try for immediate mobile failure.

If cross-site hosting must remain, assess browser-specific options only after testing. Partitioned cookies/CHIPS may be relevant in supported Chromium contexts but are not a universal Safari solution and alter storage semantics. A same-site or same-origin API path is the more robust minimal architectural solution for this flow.

## Testing checklist

Use the same exact frontend URL and backend API URL for all devices. Do not copy cookies or tokens into notes, screenshots, or logs.

### Desktop browser

- In DevTools Network, inspect the login request's `Origin`, status, and response CORS headers. Confirm the allow-origin exactly matches and credentials are allowed.
- Inspect the login response's `Set-Cookie` entries and browser cookie storage for both cookies; check rejection warnings and effective attributes.
- Inspect the session request: correct backend host, credentials included, cookie present on the outgoing request, and response status/body.
- Repeat in a clean profile and, where possible, with third-party cookies blocked to determine whether behavior tracks that policy.

### Android Chrome

- Test the production URL in current Chrome, first in a normal profile and then with third-party cookies restricted (where that control is available).
- Inspect the login response cookie warnings/storage and the subsequent session request. Confirm whether `admin_session` was stored and whether the request carried it.
- Test with any privacy/ad-blocking browser settings disabled only as a diagnostic comparison; record the settings without exposing cookie contents.
- Compare Chrome with another Android browser, noting that engines and privacy policies differ.

### iOS Safari

- Test Safari in a normal browsing session and, separately, Private Browsing.
- In Web Inspector (or remote Safari Web Inspector from a Mac), inspect login `Set-Cookie` acceptance, storage, session request cookies, HTTP status, and console CORS messages.
- Repeat with an equivalent same-site staging/API route if available. A success only in the same-site case strongly supports third-party cookie blocking.
- Test Chrome on iOS separately only as a WebKit comparison; it is not equivalent to Chrome on Android.

### Backend and logout checks

- Correlate timestamps/request IDs for login and session calls. Record cookie **presence only**, never its value. Distinguish missing-cookie 401, invalid-session 401, Firebase/service 503, and CORS/network failure.
- Confirm actual frontend origin, API host, HTTPS/redirect chain, runtime cookie mode, and CORS allowlist without exposing environment values in shared logs.
- After successful verification, test logout preflight and POST; confirm the CSRF cookie and header are present, server returns success, and deletion `Set-Cookie` targets the same API host/path.

## Uncertainties requiring browser DevTools or production logs

- Actual Render page origin, Railway API origin, custom-domain use, and whether they are cross-site.
- Actual deployment values and build-time settings for `VITE_API_BASE_URL`, `FRONTEND_ORIGINS`, and `ENVIRONMENT`.
- Whether the mobile browser accepted either `Set-Cookie` header, partitioned it, or rejected it; frontend JavaScript cannot read `Set-Cookie` directly.
- Whether the session GET reached the API, whether the request contained `admin_session`, and whether the server returned 401 or 503 on the affected device.
- Browser family/version, OS version, private mode, privacy settings, enterprise policies, and extensions/content blockers.
- Any hosting-layer redirect, proxy rewrite, or production CORS header behavior not represented in the repository.

The source response details can distinguish missing from invalid sessions in DevTools, but current application code does not log that distinction. Production evidence is necessary to establish the exact break point.

## References

- [MDN: Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Set-Cookie) — host-only cookies, `SameSite=None; Secure`, and credentialed CORS handling.
- [MDN: Request.credentials](https://developer.mozilla.org/en-US/docs/Web/API/Request/credentials) — credential inclusion affects sending cookies and respecting `Set-Cookie`.
- [MDN: CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/CORS) — exact origin matching, preflight, credentials, and browser-console diagnosis.
- [WebKit: Full Third-Party Cookie Blocking](https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/) — Safari/WebKit third-party-cookie behavior.
- [Google Privacy Sandbox: Third-party cookie restrictions](https://privacysandbox.google.com/cookies/prepare/overview) — browser settings, flags, and policy can restrict third-party cookies.
