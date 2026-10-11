# Database Architecture

## 1. Overview

DocForge uses **PostgreSQL 16** as its primary database. The schema is designed around the job processing lifecycle and supports future growth into user accounts, billing, and team features.

**Key principles:**
- Use UUIDs for all primary keys (avoid sequential ID enumeration attacks)
- Store timestamps in UTC with timezone
- Use `JSONB` columns for tool-specific configuration (avoids schema explosion per tool)
- Soft-delete for user-facing records, hard-delete for expired files
- All tables include `created_at` and `updated_at` timestamps
- Use database-level constraints for data integrity (not just application-level)

---

## 2. Entity Relationship Diagram

```
┌──────────────────────┐       ┌──────────────────────────┐
│       users           │       │      api_keys            │
│ (Tier 2)              │       │ (Tier 4)                 │
├──────────────────────┤       ├──────────────────────────┤
│ id            UUID PK │──┐    │ id              UUID PK  │
│ email         TEXT UQ  │  │    │ user_id         UUID FK  │
│ password_hash TEXT     │  │    │ key_hash        TEXT     │
│ display_name  TEXT     │  │    │ name            TEXT     │
│ avatar_url    TEXT     │  │    │ last_used_at    TIMESTZ  │
│ is_active     BOOL    │  │    │ expires_at      TIMESTZ  │
│ is_verified   BOOL    │  │    │ created_at      TIMESTZ  │
│ tier          ENUM    │  │    └──────────────────────────┘
│ created_at    TIMESTZ │  │
│ updated_at    TIMESTZ │  │
└──────────────────────┘  │
                           │
              ┌────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────┐
│                        jobs                           │
│ (MVP)                                                 │
├──────────────────────────────────────────────────────┤
│ id              UUID       PK                         │
│ user_id         UUID       FK (nullable, Tier 2)      │
│ session_id      TEXT       NOT NULL (anonymous track)  │
│ tool            TEXT       NOT NULL (e.g., "merge")    │
│ status          ENUM       NOT NULL                    │
│ config          JSONB      (tool-specific parameters)  │
│ error_message   TEXT       (nullable)                  │
│ error_code      TEXT       (nullable)                  │
│ progress        SMALLINT   (0-100, nullable)           │
│ input_files     JSONB      NOT NULL                    │
│ result_file     JSONB      (nullable)                  │
│ started_at      TIMESTZ    (nullable)                  │
│ completed_at    TIMESTZ    (nullable)                  │
│ expires_at      TIMESTZ    NOT NULL                    │
│ ip_address      INET       (rate limiting, analytics)  │
│ user_agent      TEXT       (nullable)                  │
│ created_at      TIMESTZ    NOT NULL                    │
│ updated_at      TIMESTZ    NOT NULL                    │
├──────────────────────────────────────────────────────┤
│ INDEXES:                                              │
│   idx_jobs_status          ON (status)                 │
│   idx_jobs_session_id      ON (session_id)             │
│   idx_jobs_user_id         ON (user_id) WHERE NOT NULL │
│   idx_jobs_expires_at      ON (expires_at)             │
│   idx_jobs_tool_created    ON (tool, created_at)       │
│   idx_jobs_created_at      ON (created_at)             │
└──────────────────────────────────────────────────────┘


┌──────────────────────────────────────────────────────┐
│                  usage_events                         │
│ (Tier 2 — analytics, rate limiting audit)             │
├──────────────────────────────────────────────────────┤
│ id              UUID       PK                         │
│ user_id         UUID       FK (nullable)               │
│ session_id      TEXT                                   │
│ event_type      TEXT       NOT NULL                    │
│ tool            TEXT       (nullable)                  │
│ ip_address      INET                                   │
│ metadata        JSONB      (nullable)                  │
│ created_at      TIMESTZ    NOT NULL                    │
├──────────────────────────────────────────────────────┤
│ PARTITIONED BY RANGE (created_at)                     │
│ Monthly partitions for efficient cleanup               │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│                  subscriptions                        │
│ (Tier 2)                                              │
├──────────────────────────────────────────────────────┤
│ id              UUID       PK                         │
│ user_id         UUID       FK NOT NULL UNIQUE          │
│ stripe_customer_id   TEXT  UNIQUE                      │
│ stripe_subscription_id TEXT UNIQUE                     │
│ plan            ENUM       NOT NULL                    │
│ status          ENUM       NOT NULL                    │
│ current_period_start  TIMESTZ                          │
│ current_period_end    TIMESTZ                          │
│ cancel_at_period_end  BOOL                             │
│ created_at      TIMESTZ    NOT NULL                    │
│ updated_at      TIMESTZ    NOT NULL                    │
└──────────────────────────────────────────────────────┘
```

---

## 3. Enums

```sql
-- Job status state machine (MVP)
CREATE TYPE job_status AS ENUM (
    'PENDING',       -- Job created, awaiting file uploads
    'QUEUED',        -- All files uploaded, task dispatched to worker
    'PROCESSING',    -- Worker is actively processing
    'COMPLETED',     -- Processing done, result available
    'FAILED',        -- Processing failed (see error_message)
    'CANCELLED',     -- Cancelled by user
    'EXPIRED'        -- TTL elapsed, files deleted
);



-- User tier (Tier 2)
CREATE TYPE user_tier AS ENUM ('FREE', 'PRO', 'BUSINESS', 'ENTERPRISE');

-- Subscription status (Tier 2)
CREATE TYPE subscription_status AS ENUM (
    'ACTIVE', 'PAST_DUE', 'CANCELLED', 'TRIALING', 'PAUSED'
);

-- Subscription plan (Tier 2)
CREATE TYPE subscription_plan AS ENUM ('FREE', 'PRO_MONTHLY', 'PRO_YEARLY', 'BUSINESS');
```

---

## 4. Job Status State Machine

```
                          User cancels
              ┌─────────────────────────────┐
              │                             │
              ▼                             │
PENDING ──────────────► QUEUED ──► PROCESSING ──► COMPLETED
  │                        │           │               │
  │                        │           │               │
  ▼                        ▼           ▼               ▼
CANCELLED              CANCELLED    FAILED          EXPIRED
                                        │            (after TTL)
                                        ▼
                                    (retryable?)
                                        │
                                    ┌───┴───┐
                                    │  Yes  │ → QUEUED (re-enqueue)
                                    │  No   │ → stays FAILED
                                    └───────┘
```

**Valid state transitions:**

| From | To | Trigger |
|------|----|---------|
| PENDING | QUEUED | User starts job (files verified in S3) |
| PENDING | CANCELLED | User cancels |
| QUEUED | PROCESSING | Worker picks up task |
| QUEUED | CANCELLED | User cancels before worker starts |
| PROCESSING | COMPLETED | Worker finishes successfully |
| PROCESSING | FAILED | Worker encounters error or stalled timeout |
| COMPLETED | EXPIRED | Cleanup task runs after TTL |
| FAILED | QUEUED | Retry (if eligible) |
| Any terminal state | — | No further transitions allowed |

---

## 5. JSONB Config Examples

The `config` column on `jobs` stores tool-specific parameters:

**Merge:**
```json
{
  "file_order": ["file-uuid-1", "file-uuid-2", "file-uuid-3"]
}
```

**Split:**
```json
{
  "mode": "ranges",
  "ranges": ["1-5", "6-10", "11-15"]
}
```

**Compress:**
```json
{
  "quality": "medium"
}
```

**Rotate:**
```json
{
  "rotations": {
    "file-uuid-1": {
      "pages": "all",
      "degrees": 90
    }
  }
}
```

---

## 6. Migration Strategy

- Use **Alembic** for all schema changes
- Never modify production data manually
- All migrations must be reversible (include `downgrade()`)
- Migrations are numbered sequentially and stored in `backend/alembic/versions/`
- Run migrations in CI before deployment
- Large data migrations should use batched operations to avoid locking

---

## 7. Data Retention

| Data Type | Retention | Mechanism |
|-----------|-----------|-----------|
| Input/output files | 2 hours (free), 24 hours (pro) | Celery Beat cleanup task |
| Job records (anonymous) | 30 days | Celery Beat purge task |
| Job records (authenticated) | 1 year | User can delete manually |
| User accounts | Until deletion requested | GDPR compliance |
| Usage events | 90 days | Table partitioning + drop old partitions |
| Audit logs | 1 year | Compliance requirement |

---

## 8. Indexing Strategy

Indexes are designed for the most common query patterns:

| Query Pattern | Index |
|---------------|-------|
| Get job by ID | Primary key |
| List jobs by session | `idx_jobs_session_id` |
| List jobs by user | `idx_jobs_user_id` (partial) |
| Find expired jobs for cleanup | `idx_jobs_expires_at` |
| Analytics by tool + date | `idx_jobs_tool_created` |
| Find expired files | `idx_jobs_expires_at` |

---

## 9. Security Considerations

- **UUIDs prevent enumeration**: Job IDs and file IDs are UUIDv4, not sequential integers
- **No cascading deletes from user → jobs**: Users can request data deletion through an explicit process
- **IP addresses stored for rate limiting**: Hashed or anonymized after 30 days for privacy
- **Passwords hashed with bcrypt** (cost factor 12)
- **Connection pooling**: Use PgBouncer or SQLAlchemy async pool in production
- **Row-level security considered** for multi-tenant (Tier 5 only)
