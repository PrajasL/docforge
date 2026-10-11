# DocForge Production Deployment & Operations Guide

This guide details the complete production deployment pipeline, storage architecture, monitoring integration, health observability, backup/recovery protocols, and rollback procedures for DocForge.

---

## 1. Architecture Overview

In production, DocForge runs as an isolated containerized ecosystem:

```
                      Internet / Users
                            │
                            ▼
              ┌───────────────────────────┐
              │ Reverse Proxy (Caddy/TLS) │ (Ports 80, 443)
              └─────────────┬─────────────┘
                            │
             ┌──────────────┴──────────────┐
             │                             │
    /api/*, /health*                    /* (Web)
             │                             │
             ▼                             ▼
    ┌─────────────────┐           ┌──────────────────┐
    │ FastAPI Backend │           │ Next.js Frontend │
    │   (Non-root)    │           │ (Standalone Node)│
    └────────┬────────┘           └──────────────────┘
             │
     ┌───────┼──────────────────────────────┐
     │       │                              │
     ▼       ▼                              ▼
┌─────────┐ ┌─────────┐              ┌──────────────┐
│Postgres │ │  Redis  │ ◄──────────► │Celery Workers│
│  (16)   │ │   (7)   │              │   & Beat     │
└─────────┘ └─────────┘              └──────┬───────┘
     ▲                                      │
     │                                      ▼
     │                               ┌──────────────┐
     │                               │    ClamAV    │
     │                               │Daemon (clamd)│
     │                               └──────────────┘
     ▼
┌──────────────────────────────────────────────────┐
│ Cloudflare R2 / AWS S3 Production Object Storage │
└──────────────────────────────────────────────────┘
```

### Security Architecture Highlights
- **Internal-only data plane:** PostgreSQL, Redis, and ClamAV do NOT expose host ports.
- **Least privilege users:** Frontend runs as non-root `nextjs` (UID 1001); Backend runs as non-root `appuser` (UID 10001).
- **Resource isolation:** CPU and memory caps prevent memory-heavy PDF processing from starving system services.
- **Fail-closed antivirus:** Malicious uploads and scanner connectivity failures are blocked before any PDF processing.
- **Data protection:** Presigned URLs expire in 5–15 minutes; expired job files are purged automatically every 15 minutes by Celery Beat.

---

## 2. Production Storage Setup (Cloudflare R2 & AWS S3)

DocForge uses an abstract storage layer (`S3StorageBackend`) that seamlessly supports **Cloudflare R2**, **AWS S3**, and local **MinIO**.

### 2.1 Cloudflare R2 Setup
1. Log into your Cloudflare dashboard and navigate to **R2**.
2. Create two buckets:
   - `docforge-inputs` (for temporary uploaded files awaiting processing)
   - `docforge-outputs` (for processed PDF artifacts ready for user download)
3. Set **Object Lifecycle Rules** in Cloudflare R2 for both buckets:
   - Expire objects after **1 day** (ensures automated bucket cleanup even if worker cleanup fails).
4. Navigate to **Manage R2 API Tokens** and create a token with:
   - Permissions: **Object Read & Write** on the `docforge-inputs` and `docforge-outputs` buckets.
5. Note your Account ID, Access Key ID, and Secret Access Key.
6. Configure in `.env.production`:
   ```bash
   STORAGE_PROVIDER=r2
   STORAGE_ENDPOINT=https://<YOUR_ACCOUNT_ID>.r2.cloudflarestorage.com
   STORAGE_REGION=auto
   STORAGE_ACCESS_KEY=<YOUR_R2_ACCESS_KEY_ID>
   STORAGE_SECRET_KEY=<YOUR_R2_SECRET_ACCESS_KEY>
   STORAGE_BUCKET_INPUTS=docforge-inputs
   STORAGE_BUCKET_OUTPUTS=docforge-outputs
   STORAGE_USE_SSL=true
   ```

### 2.2 AWS S3 Setup
If deploying to AWS:
1. Create buckets `docforge-inputs` and `docforge-outputs`.
2. Attach an IAM policy granting `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject`, `s3:HeadObject`, and `s3:HeadBucket`.
3. Configure in `.env.production`:
   ```bash
   STORAGE_PROVIDER=s3
   STORAGE_ENDPOINT=https://s3.us-east-1.amazonaws.com
   STORAGE_REGION=us-east-1
   STORAGE_ACCESS_KEY=<YOUR_AWS_ACCESS_KEY_ID>
   STORAGE_SECRET_KEY=<YOUR_AWS_SECRET_ACCESS_KEY>
   ```

---

## 3. Monitoring & Telemetry with Sentry

DocForge includes optional Sentry integration for real-time exception tracking and performance tracing.

### 3.1 Enabling Sentry
Set `SENTRY_DSN` in `.env.production`:
```bash
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```
If `SENTRY_DSN` is empty or unset, telemetry is automatically disabled with zero runtime overhead.

### 3.2 Data Privacy & PII Scrubbing Guarantees
DocForge enforces strict telemetry data filtering:
- **Zero PDF leakage:** All request payloads with `Content-Type: multipart/form-data`, `application/pdf`, or raw binary byte buffers are scrubbed to `[FILTERED_UPLOAD_PAYLOAD]`.
- **Credential sanitization:** Headers (`Authorization`, `Cookie`, `Set-Cookie`, `X-Session-Id`, `X-Api-Key`) are stripped.
- **Field scrubbing:** Dictionary keys matching `password`, `secret`, `token`, `key`, `credential`, or `auth` are replaced with `[FILTERED]`.
- **Query param sanitization:** S3 presigned signatures (`X-Amz-Signature`, `X-Amz-Credential`, `X-Amz-Security-Token`) are stripped from all breadcrumbs and exception URLs.

---

## 4. Health Checks & Observability

DocForge provides dedicated liveness and readiness endpoints:

| Endpoint | Probe Type | Purpose | Behavior |
| :--- | :--- | :--- | :--- |
| `/health` or `/health/live` | **Liveness** | Container process liveness | Returns HTTP 200 immediately if FastAPI process is active. Used by Docker `HEALTHCHECK` and Kubernetes `livenessProbe`. |
| `/health/ready` | **Readiness** | Full dependency health | Checks PostgreSQL, Redis, Storage (R2/S3/MinIO), Celery workers, and ClamAV. Returns HTTP 200 if ready, HTTP 503 if degraded/offline. |

### Sample Response (`/health/ready`):
```json
{
  "success": true,
  "data": {
    "status": "ready",
    "application": {
      "status": "healthy",
      "service": "DocForge",
      "version": "1.0.0",
      "environment": "production"
    },
    "dependencies": {
      "database": { "status": "connected" },
      "redis": { "status": "connected" },
      "storage": {
        "status": "connected",
        "provider": "r2",
        "buckets_available": ["docforge-inputs", "docforge-outputs"]
      },
      "workers": {
        "status": "connected",
        "workers_online": 4,
        "workers": ["celery@worker-1", "celery@worker-2"]
      },
      "malware_scanner": {
        "status": "connected",
        "enabled": true,
        "host": "clamav",
        "port": 3310,
        "fail_closed": true
      }
    }
  }
}
```

---

## 5. Deployment Step-by-Step

### 5.1 Initial Setup
1. Clone the repository onto the production server.
2. Create your production environment file from the template:
   ```bash
   cp .env.production.example .env.production
   chmod 600 .env.production
   ```
3. Populate `.env.production` with:
   - A generated secret key: `openssl rand -hex 32`
   - A secure database password
   - R2 / S3 credentials
   - Your production domain (`APP_DOMAIN=docforge.yourdomain.com`)

### 5.2 Build & Launch Containers
```bash
# Build multi-stage images and start all services in detached mode
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### 5.3 Apply Database Migrations
Run Alembic migrations inside the running backend container:
```bash
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 5.4 Verify Deployment Status
```bash
# Check running containers
docker compose -f docker-compose.prod.yml ps

# Verify readiness endpoint
curl -f http://localhost:80/health/ready
```

---

## 6. Reverse Proxy & HTTPS

DocForge includes out-of-the-box support for **Caddy** with automated HTTPS via Let's Encrypt / ZeroSSL.

### Using Caddy (Default)
When `APP_DOMAIN` is configured to a valid public domain (e.g., `docforge.example.com`) and DNS A/AAAA records point to your server IP, Caddy will automatically provision and renew SSL certificates with zero manual intervention.

### Using External Nginx / Cloudflare
If using an external Nginx instance or Cloudflare Edge SSL:
- Review `docker/nginx.conf` for optimized proxy timeouts (300s for large files) and streaming configurations (`proxy_buffering off` for SSE).
- Ensure `TRUSTED_PROXIES` in `.env.production` contains the upstream proxy IP/CIDR so client rate limiting and IP logging work correctly.

---

## 7. Backup and Recovery Protocol

### 7.1 PostgreSQL Database Backups
Automate daily database backups via cron:
```bash
#!/usr/bin/env bash
BACKUP_DIR="/var/backups/docforge"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

docker compose -f /opt/docforge/docker-compose.prod.yml exec -T postgres \
  pg_dump -U docforge_app docforge_prod | gzip > "$BACKUP_DIR/db_$TIMESTAMP.sql.gz"

# Retain backups for 14 days
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete
```

### 7.2 Database Restoration
To restore from a backup:
```bash
gunzip < /var/backups/docforge/db_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres psql -U docforge_app -d docforge_prod
```

### 7.3 Object Storage Recovery
Because PDF files in DocForge are ephemeral and automatically expired after user download (default TTL: 1 hour; R2 retention: 24 hours), storage backups of user PDFs are intentionally not required. Permanent configuration and templates are stored in version control.

---

## 8. Zero-Downtime Updates & Rollback

### 8.1 Zero-Downtime Deployment
```bash
# 1. Pull latest code
git pull origin main

# 2. Build updated images
docker compose -f docker-compose.prod.yml --env-file .env.production build

# 3. Apply schema migrations
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 4. Rolling restart of backend and frontend
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --no-deps backend frontend worker beat

# 5. Verify readiness
curl -f http://localhost:80/health/ready || (echo "Deployment failed! Initiating rollback..." && exit 1)
```

### 8.2 Rollback Procedure
If a deployment fails the readiness probe or encounters critical regressions:
```bash
# 1. Revert to previous Git commit or tagged release
git checkout <PREVIOUS_COMMIT_OR_TAG>

# 2. Downgrade database schema if migration was applied
docker compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# 3. Rebuild and restart services
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```
