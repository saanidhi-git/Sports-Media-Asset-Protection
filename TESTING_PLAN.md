# Comprehensive Full-Stack Testing Implementation Plan
**Project:** Shield Media Asset Protection
**Stack:** Angular (Frontend) | FastAPI (Backend) | PostgreSQL (Database)
**Lead QA Engineer:** Senior Systems Testing Architect

---

## 1. Executive Summary & Strategy
This document outlines the end-to-end quality assurance strategy. We utilize the **Testing Pyramid** to balance execution speed with system confidence. 

### Core Goals:
*   **Zero-Regression Policy:** Every PR must pass automated regression suites.
*   **Data Integrity:** Ensure neural fingerprints and dispatch logs are 100% accurate.
*   **Security First:** Rigorous testing of JWT flows and PII (Personally Identifiable Information) handling.

---

## 2. Backend Testing Layer (FastAPI)
### Tools: `pytest`, `pytest-asyncio`, `httpx`, `AlchemyMock`, `Faker`

#### 2.1 Unit Testing (Logic Isolation)
*   **Service Layer:** Test `app/services/fingerprint/` and `app/services/scoring/` using static data. Verify that similarity math matches expected forensic thresholds.
*   **Pydantic Validation:** Test all schemas in `app/schemas/`. Ensure malformed email strings or negative numeric limits trigger `422 Unprocessable Entity`.

#### 2.2 Integration Testing (The Data Loop)
*   **Database Isolation:** Use a dedicated test database (PostgreSQL container). Use SQLAlchemy "Function Scope" fixtures to rollback transactions after each test.
*   **Repository Pattern:** Test CRUD operations directly against the DB to ensure complex joins (like the Human Review Queue) return correct results.
*   **Mocking External Deps:** 
    *   **SMTP:** Mock the `smtplib` connection to verify HTML generation without sending real emails.
    *   **External APIs:** Mock YouTube/Reddit API responses using `respx` or `unittest.mock`.

#### 2.3 API Level Testing (Contract Verification)
*   **FastAPI TestClient:** Validate all V1 endpoints.
*   **Error Handling:** Explicitly test `401 Unauthorized`, `403 Forbidden`, and `404 Not Found` scenarios.
*   **Auto-Documentation Sync:** Use `Schemathesis` to perform property-based testing against the generated `openapi.json` to ensure the API never drifts from its specification.

---

## 3. Frontend Testing Layer (Angular)
### Tools: `Vitest`, `Playwright`, `Angular Testing Library`

#### 3.1 Unit & Component Testing
*   **Signal State Testing:** Verify that Angular Signals in `HumanReviewDetail` update correctly when the `PipelineService` returns data.
*   **Mocking Services:** Use `provideHttpClientTesting` to intercept and mock backend responses, ensuring the UI handles loading/error states gracefully.
*   **Visual Regression:** Test that components render correctly within CSS budgets (monitored via `angular.json`).

#### 3.2 UI/UX Logic
*   **Guard Testing:** Ensure `AuthGuard` correctly blocks unauthorized access to `/human-review`.
*   **Intercept logic:** Verify that the JWT interceptor correctly attaches the `Authorization: Bearer` header to outgoing requests.

---

## 4. End-to-End (E2E) Testing (System Flow)
### Tool: `Playwright` (Headless Browser)

We will automate "Critical User Journeys" (CUJs):
1.  **The Enforcement Path:**
    *   Navigate to Login -> Enter Credentials.
    *   Search for a known infringing asset.
    *   Navigate to Review Queue.
    *   Open Case Detail -> Verify Forensic Charting.
    *   Click "Authorize & Dispatch" -> Enter Recipient -> Confirm.
    *   **Verification:** Check the UI for the "DISPATCHED" badge and ensure the record appears in "Enforcement History".
2.  **Cross-Browser Check:** Run the suite on Chromium, Firefox, and WebKit to ensure CSS compatibility (especially blur filters and neon glow effects).

---

## 5. Non-Functional Testing

### 5.1 Performance & Load (Locust)
*   **Baseline:** 50 concurrent operators polling the queue.
*   **Stress Test:** Simulate background scan jobs processing 100+ videos simultaneously while an operator attempts to dispatch a notice.

### 5.2 Security (OWASP Focus)
*   **Injection:** Test search inputs for SQLi and XSS.
*   **Broken Access Control:** Verify that User A cannot view Scan Logs belonging to User B.
*   **Directory Traversal:** Ensure the `/uploads` proxy only serves files within the intended subdirectories.

---

## 6. CI/CD Integration

The pipeline (GitHub Actions/GitLab CI) will execute in this order:
1.  **Lint & Style:** `ruff` (Python), `eslint` (TS), `prettier --check`.
2.  **Type Safety:** `mypy` and `tsc --noEmit`.
3.  **Fast Track:** Run all Unit Tests (Target: < 2 mins).
4.  **Database Track:** Run Integration Tests with a transient DB.
5.  **Build Gate:** `npm run build` (Production mode).
6.  **Full System:** Deploy to a staging environment and run Playwright E2E suite.

---

## 7. Metrics & Reporting
*   **Code Coverage:** Minimum 85% on backend services; 75% on frontend components.
*   **Defect Density:** Track bugs found in production vs. testing.
*   **Audit Log:** Daily auto-generated report showing "Successful Dispatches vs. API Failures".

---
**Approved by:** 🛡️ SHIELD MEDIA Quality Engineering Team
**Date:** April 2026
