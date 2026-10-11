# API Specification

## 1. Overview

DocForge exposes a **versioned REST API** under `/api/v1/`. All requests and responses use JSON (except file uploads/downloads). Authentication is optional for MVP (anonymous usage via session tokens).

**Base URL:** `https://api.docforge.com/api/v1` (production)
**Local:** `http://localhost:8000/api/v1`

---

## 2. API Design Principles

1. **Consistent response envelope** — All responses use a standard wrapper
2. **Descriptive error codes** — Machine-readable error codes + human messages
3. **Pagination** — Cursor-based for lists
4. **Idempotent** — PUT/DELETE operations are idempotent
5. **Rate limited** — Per-IP and per-user (when authenticated)
6. **Versioned** — `/api/v1/` prefix; breaking changes require new version

### Standard Response Envelope

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-10-08T18:00:00Z"
  }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "File size exceeds maximum allowed (50 MB)",
    "details": [
      {
        "field": "files[0]",
        "message": "File is 78 MB, maximum is 50 MB"
      }
    ]
  },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-10-08T18:00:00Z"
  }
}
```

---

## 3. MVP Endpoints

### 3.1 Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (no auth) |
| GET | `/health/ready` | Readiness check (DB + Redis + Storage) |

---

### 3.2 Jobs

#### Create Job
```
POST /api/v1/jobs
```

Creates a new processing job and returns presigned upload URLs for input files.

**Request:**
```json
{
  "tool": "merge",
  "files": [
    { "name": "report.pdf", "size": 1048576, "content_type": "application/pdf" },
    { "name": "appendix.pdf", "size": 524288, "content_type": "application/pdf" }
  ],
  "config": {
    "file_order": []
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "job": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "tool": "merge",
      "status": "PENDING",
      "config": { "file_order": [] },
      "expires_at": "2026-10-08T20:00:00Z",
      "created_at": "2026-10-08T18:00:00Z"
    },
    "uploads": [
      {
        "file_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "upload_url": "https://storage.example.com/inputs/...",
        "upload_method": "PUT",
        "upload_headers": {
          "Content-Type": "application/pdf"
        },
        "expires_in": 900
      },
      {
        "file_id": "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        "upload_url": "https://storage.example.com/inputs/...",
        "upload_method": "PUT",
        "upload_headers": {
          "Content-Type": "application/pdf"
        },
        "expires_in": 900
      }
    ]
  }
}
```

**Error codes:**
- `INVALID_TOOL` — Tool name not recognized
- `TOO_MANY_FILES` — Exceeds file count limit
- `FILE_TOO_LARGE` — Individual file exceeds size limit
- `TOTAL_SIZE_EXCEEDED` — Combined file size exceeds limit
- `INVALID_CONTENT_TYPE` — File type not supported for this tool
- `RATE_LIMIT_EXCEEDED` — Too many jobs created

---



#### Start Job
```
POST /api/v1/jobs/{job_id}/start
```

Validates all files are uploaded by checking Object Storage, then enqueues the processing task.

**Request (optional config update):**
```json
{
  "config": {
    "file_order": [
      "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
      "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    ]
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "job": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "QUEUED",
      "estimated_duration_seconds": 5
    }
  }
}
```

**Error codes:**
- `JOB_NOT_FOUND` — Job does not exist or is not accessible
- `FILES_NOT_READY` — Not all files have been uploaded
- `INVALID_CONFIG` — Config validation failed
- `JOB_ALREADY_STARTED` — Job has already been started

---

#### Get Job Status
```
GET /api/v1/jobs/{job_id}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "job": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "tool": "merge",
      "status": "COMPLETED",
      "progress": 100,
      "config": { "file_order": ["..."] },
      "input_files": [
        {
          "id": "6ba7b810-...",
          "original_name": "report.pdf",
          "size_bytes": 1048576,
          "page_count": 12
        }
      ],
      "result_file": {
        "id": "7ca8c920-...",
        "original_name": "merged.pdf",
        "size_bytes": 1572864,
        "page_count": 24
      },
      "error_message": null,
      "started_at": "2026-10-08T18:00:01Z",
      "completed_at": "2026-10-08T18:00:04Z",
      "expires_at": "2026-10-08T20:00:00Z",
      "created_at": "2026-10-08T18:00:00Z"
    }
  }
}
```

---

#### Stream Job Progress (SSE)
```
GET /api/v1/jobs/{job_id}/progress
```

Server-Sent Events stream for real-time progress updates.

**Event stream:**
```
event: status
data: {"status": "QUEUED", "progress": 0}

event: status
data: {"status": "PROCESSING", "progress": 25}

event: progress
data: {"progress": 50, "message": "Merging page 6 of 12..."}

event: progress
data: {"progress": 100}

event: completed
data: {"status": "COMPLETED", "result_file": {"original_name": "merged.pdf", "size_bytes": 1572864}}
```

---

#### Cancel Job
```
POST /api/v1/jobs/{job_id}/cancel
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "job": {
      "id": "550e8400-...",
      "status": "CANCELLED"
    }
  }
}
```

---

### 3.3 Files

#### Get Download URL
```
GET /api/v1/jobs/{job_id}/download
```

Returns a time-limited presigned download URL for the job's result file.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "download_url": "https://storage.example.com/outputs/...",
    "expires_in": 300,
    "filename": "merged.pdf",
    "size_bytes": 1572864,
    "content_type": "application/pdf"
  }
}
```

**Error codes:**
- `FILE_NOT_FOUND` — File does not exist
- `FILE_EXPIRED` — File has been cleaned up
- `JOB_NOT_COMPLETED` — Job hasn't finished processing yet
- `ACCESS_DENIED` — File belongs to another session/user

---

### 3.4 Tools

#### List Available Tools
```
GET /api/v1/tools
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "tools": [
      {
        "id": "merge",
        "name": "Merge PDF",
        "description": "Combine multiple PDFs into one document",
        "category": "organize",
        "icon": "merge-icon",
        "min_files": 2,
        "max_files": 20,
        "accepted_types": ["application/pdf"],
        "max_file_size_bytes": 52428800,
        "requires_auth": false,
        "is_available": true
      },
      {
        "id": "split",
        "name": "Split PDF",
        "description": "Split a PDF into multiple documents",
        "category": "organize",
        "min_files": 1,
        "max_files": 1,
        "accepted_types": ["application/pdf"],
        "max_file_size_bytes": 52428800,
        "requires_auth": false,
        "is_available": true
      }
    ]
  }
}
```

#### Get Tool Details
```
GET /api/v1/tools/{tool_id}
```

Returns tool metadata + config schema (JSON Schema for the `config` field).

---

## 4. Authentication Endpoints (Tier 2)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register with email/password |
| POST | `/api/v1/auth/login` | Login, returns JWT |
| POST | `/api/v1/auth/logout` | Invalidate session |
| POST | `/api/v1/auth/refresh` | Refresh JWT |
| POST | `/api/v1/auth/forgot-password` | Send reset email |
| POST | `/api/v1/auth/reset-password` | Reset with token |
| GET | `/api/v1/auth/me` | Get current user profile |
| PATCH | `/api/v1/auth/me` | Update profile |
| DELETE | `/api/v1/auth/me` | Delete account (GDPR) |
| GET | `/api/v1/auth/oauth/{provider}` | Initiate OAuth flow |
| GET | `/api/v1/auth/oauth/{provider}/callback` | OAuth callback |

## 5. Billing Endpoints (Tier 2)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/billing/plans` | List available plans |
| POST | `/api/v1/billing/checkout` | Create Stripe checkout session |
| POST | `/api/v1/billing/portal` | Create Stripe customer portal |
| POST | `/api/v1/billing/webhooks/stripe` | Stripe webhook handler |
| GET | `/api/v1/billing/subscription` | Get current subscription |

## 6. Public API Endpoints (Tier 4)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/public/jobs` | Create job via API key |
| GET | `/api/v1/public/jobs/{id}` | Get job status |
| GET | `/api/v1/public/usage` | Get API usage stats |

---

## 7. Rate Limits

| Tier | Jobs/hour | Uploads/hour | Downloads/hour |
|------|-----------|-------------|----------------|
| Anonymous | 10 | 20 | 20 |
| Free (authenticated) | 25 | 50 | 50 |
| Pro | 100 | 200 | 200 |
| Business | 500 | 1000 | 1000 |
| API | 1000 | 2000 | 2000 |

Rate limit headers included in all responses:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1696789200
```

---

## 8. Error Code Registry

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `INVALID_TOOL` | 400 | Unknown tool identifier |
| `JOB_NOT_FOUND` | 404 | Job does not exist |
| `FILE_NOT_FOUND` | 404 | File does not exist |
| `FILE_EXPIRED` | 410 | File has been cleaned up |
| `JOB_ALREADY_STARTED` | 409 | Job has already been started |
| `FILES_NOT_READY` | 409 | Not all files uploaded |
| `INVALID_CONFIG` | 422 | Tool config validation failed |
| `FILE_TOO_LARGE` | 413 | File exceeds size limit |
| `TOTAL_SIZE_EXCEEDED` | 413 | Combined files exceed limit |
| `TOO_MANY_FILES` | 400 | Too many files for this tool |
| `INVALID_CONTENT_TYPE` | 415 | File type not accepted |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit hit |
| `ACCESS_DENIED` | 403 | Not authorized for this resource |
| `UNAUTHORIZED` | 401 | Authentication required |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `SERVICE_UNAVAILABLE` | 503 | System overloaded or in maintenance |

---

## 9. Session Management (MVP)

For the MVP (no user accounts), we use a **session-based approach**:

1. On first visit, frontend generates a UUIDv4 `session_id` and stores it in `localStorage`
2. All API requests include `X-Session-Id: <uuid>` header
3. Backend uses `session_id` to scope job access — a user can only view/download jobs created in their session
4. This provides basic access control without requiring authentication
5. When auth is added (Tier 2), sessions are linked to user accounts

**Security note:** Session IDs are UUIDv4 (unguessable). Combined with UUIDv4 job IDs, enumeration attacks are computationally infeasible.
