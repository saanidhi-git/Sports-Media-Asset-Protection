# 🛡️ SHIELD_MEDIA: Automated Takedown Protocol

This document outlines the architectural plan for implementing the **SMTP-based Automated Takedown Dispatch** system.

## 1. SMTP Backend Architecture (Python)

### 🛰️ Connection Configuration
We will implement an asynchronous SMTP dispatcher using `aiosmtplib`. The following parameters are required in the `.env` file:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `SMTP_HOST` | SMTP Server Host | `smtp.gmail.com` |
| `SMTP_PORT` | Port (TLS/SSL) | `587` |
| `SMTP_USER` | Authorized Sender | `legal@shieldmedia.ai` |
| `SMTP_PASS` | App Password / Key | `xxxx-xxxx-xxxx-xxxx` |
| `SENDER_NAME` | Display Name | `Shield Media Enforcement` |

### 🧠 Logic Flow
1. **Trigger**: Operator clicks "Authorize & Dispatch" on the frontend.
2. **Data Fetching**: Backend retrieves `DetectionResult` and the original `Asset` metadata (Owner, Title, Match Score).
3. **Template Rendering**: A `Jinja2` HTML template is populated with the specific forensic evidence (Suspect URL, Hash ID, Timestamp).
4. **Dispatch**: The email is sent asynchronously.
5. **State Mutation**: The `DetectionResult.verdict` is updated to `DISPATCHED` in the database.

### 📦 Dependencies
```bash
pip install aiosmtplib jinja2
```

---

## 2. API Endpoint Specification

### `POST /api/pipeline/takedown/dispatch`
**Description**: Initiates the email takedown notice for a specific detection.

**Payload**:
```json
{
  "detection_id": 123,
  "recipient_override": "optional@platform.com",
  "custom_notes": "Additional context for the platform..."
}
```

**Response**:
```json
{
  "status": "success",
  "message": "Enforcement notice dispatched to [platform]",
  "timestamp": "2026-04-25T14:30:00Z"
}
```

---

## 3. Frontend Enforcement Interface (Angular)

### 🖥️ Dispatch Interaction
* **Button Component**: The "Authorize & Dispatch" button will hook into the `PipelineService.dispatchTakedown(id)`.
* **Visual Feedback**:
    * **State 1**: `DISPATCH` (Primary Action).
    * **State 2**: `DISPATCHING...` (Loading).
    * **State 3**: `DISPATCHED` (Success / Disabled).

### 📋 The "Dispatched" Queue
A new view/filter will be added to the Human Review module to track active actions:
* **Filter Bar**: `[ All | Pending | Dispatched ]`.
* **Badge System**: Items in the `Dispatched` state will show a cyan `ENFORCED` badge with a "Sent" timestamp.
* **Audit Log**: A new tab in the `HumanReviewDetail` showing the history of enforcement (who sent it, when, and to where).

---

---

## 4. Implementation Milestones

1. **Phase 1**: Environment setup and SMTP connectivity test script.
2. **Phase 2**: Email template design (Legal-Professional tone).
3. **Phase 3**: Backend service and API endpoint implementation.
4. **Phase 4**: Frontend UI updates (Button logic + Dispatched Queue).

---

## 5. Deployment Strategy

### 🛡️ Production Security
* **Port Management**: Standard cloud providers (AWS, Azure, GCP) block outgoing traffic on Port 25. The system is designed to use **Port 587 (STARTTLS)** for maximum compatibility and security.
* **Secret Management**: In production, SMTP credentials must be injected via **Environment Secrets** (e.g., GitHub Secrets, Docker ENV, or Kubernetes Secrets) rather than static `.env` files.
* **Deliverability**: To prevent enforcement notices from being flagged as spam, it is recommended to configure **SPF, DKIM, and DMARC** records for the sender domain.

### 🔄 Failover & Logging
* **Retry Logic**: If the SMTP server is temporarily unreachable, the system will log a `SMTP_DISPATCH_FAILURE` and keep the detection in the `REVIEW` state for a retry.
* **Audit Trail**: Every dispatched email is logged with a unique `Message-ID` in the application logs for forensic verification.

---

## 6. Required Operator Inputs
To initiate Phase 1, the following data is required:
1. **SMTP Provider Info**: Host and Port.
2. **App-Specific Credentials**: Username and App Password.
3. **Test Recipient**: An internal email to verify the template rendering and delivery.
