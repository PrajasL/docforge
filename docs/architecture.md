# System Architecture

## 1. Architecture Overview

DocForge uses a **modular monolith** architecture with background workers. All backend logic lives in a single Python codebase organized into domain modules, with Celery workers handling async processing.

### Why modular monolith?
- **Simplicity**: One codebase, one deployment pipeline, one database
- **Refactoring ease**: Module boundaries can become microservice boundaries later if needed
- **Developer velocity**: No inter-service communication overhead, shared types, single debugging context
- **Sufficient for scale**: A well-structured monolith with async workers can handle thousands of concurrent users

### When to split into services
Only extract a service when:
1. A module needs independent scaling (e.g., OCR workers on GPU nodes)
2. A module needs a different language/runtime
3. Team size exceeds ~8 developers on the backend
4. Deployment frequency of one module is 10x another

---

## 2. High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USERS (Browser)                             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND (SSR/SSG)                      │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐   │
│  │ Tool     │  │ Upload   │  │ Job      │  │ SEO Landing       │   │
│  │ Pages    │  │ Manager  │  │ Tracker  │  │ Pages (SSG)       │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘   │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (REST API)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (API Server)                    │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ Jobs     │  │ Files    │  │ Auth     │  │ Tools            │   │
│  │ Module   │  │ Module   │  │ Module   │  │ Registry         │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────────────┘   │
│       │              │             │              │                  │
│  ┌────▼──────────────▼─────────────▼──────────────▼─────────────┐   │
│  │                   SHARED DOMAIN LAYER                         │   │
│  │  (models, schemas, services, validators, storage abstraction) │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────┬─────────────────┬──────────────────┬───────────────────────┘
         │                 │                  │
         ▼                 ▼                  ▼
┌────────────────┐ ┌───────────────┐ ┌────────────────────────────────┐
│  PostgreSQL    │ │ Redis         │ │ Object Storage (S3-compatible) │
│                │ │               │ │                                │
│  - Jobs        │ │ - Task queue  │ │ - Input files                  │
│  - Users       │ │ - Task results│ │ - Output files                 │
│  - Files meta  │ │ - Rate limits │ │ - Thumbnails                   │
│  - Usage logs  │ │ - Sessions    │ │                                │
│                │ │ - Cache       │ │ Local: MinIO                   │
└────────────────┘ └───────┬───────┘ │ Prod:  Cloudflare R2 / AWS S3 │
                           │         └────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CELERY WORKERS                                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    WORKER PROCESS                             │   │
│  │                                                              │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐   │   │
│  │  │ Merge   │  │ Split   │  │Compress │  │ Future tools │   │   │
│  │  │ Handler │  │ Handler │  │ Handler │  │ ...          │   │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬───────┘   │   │
│  │       │             │            │              │            │   │
│  │  ┌────▼─────────────▼────────────▼──────────────▼────────┐  │   │
│  │  │              BASE PROCESSING PIPELINE                  │  │   │
│  │  │                                                        │  │   │
│  │  │  1. Download input from Object Storage                 │  │   │
│  │  │  2. Validate file (size, type, structure)              │  │   │
│  │  │  3. Execute tool-specific logic                        │  │   │
│  │  │  4. Upload result to Object Storage                    │  │   │
│  │  │  5. Update job status in PostgreSQL                    │  │   │
│  │  │  6. Clean up temp files                                │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 CLEANUP WORKER (Celery Beat)                 │   │
│  │                                                              │   │
│  │  - Delete expired files from Object Storage                  │   │
│  │  - Transition expired jobs to EXPIRED state                  │   │
│  │  - Purge old job records (configurable retention)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### Frontend

| Technology | Version | Purpose | License | Why chosen |
|-----------|---------|---------|---------|------------|
| **Next.js** | 15.x | React framework, SSR/SSG | MIT | SEO via SSG, API routes for BFF, mature ecosystem |
| **TypeScript** | 5.x | Type safety | Apache-2.0 | Catches bugs at compile time, better DX |
| **Tailwind CSS** | 4.x | Utility-first CSS | MIT | Rapid UI development, consistent design |
| **shadcn/ui** | latest | Component library | MIT | Accessible, customizable, not a dependency (copied into project) |
| **React DnD** or **dnd-kit** | latest | Drag-and-drop | MIT | File reordering UI for merge/reorder tools |
| **react-dropzone** | latest | File upload zone | MIT | Battle-tested drag-and-drop file upload |
| **Zustand** | latest | Client state management | MIT | Lightweight, minimal boilerplate vs Redux |

### Backend

| Technology | Version | Purpose | License | Why chosen |
|-----------|---------|---------|---------|------------|
| **Python** | 3.12+ | Backend language | PSF | Rich PDF ecosystem, team familiarity |
| **FastAPI** | 0.110+ | HTTP API framework | MIT | Async, auto-docs, Pydantic validation, performance |
| **Pydantic** | 2.x | Data validation/serialization | MIT | FastAPI integration, strict typing |
| **SQLAlchemy** | 2.x | ORM / database toolkit | MIT | Mature, async support, migration-friendly |
| **Alembic** | latest | Database migrations | MIT | SQLAlchemy companion, reliable migrations |
| **Celery** | 5.x | Task queue / workers | BSD-3 | Mature, proven at scale, rich monitoring |
| **Redis** | 7.x | Message broker + cache | BSD-3 | Fast, Celery broker, rate limiting, caching |
| **PostgreSQL** | 16.x | Primary database | PostgreSQL License | ACID, JSON support, mature, scalable |
| **boto3 / aioboto3** | latest | S3-compatible storage client | Apache-2.0 | Works with MinIO, S3, R2 via endpoint config |
| **Flower** | latest | Celery monitoring dashboard | BSD-3 | Real-time task monitoring |

### PDF Processing Libraries

| Library | License | Purpose | Notes |
|---------|---------|---------|-------|
| **pypdf** | BSD-3 | Merge, split, rotate, extract, metadata | ✅ Permissive, pure Python, safe for commercial use |
| **pikepdf** | MPL-2.0 | Compress, repair, encrypt/decrypt, linearize | ⚠️ MPL-2.0: can use commercially but modifications to pikepdf itself must be shared. Wrapper around QPDF (Apache-2.0). Fine for use as-is. |
| **Pillow** | HPND (permissive) | Image conversion (JPG/PNG ↔ PDF) | ✅ Permissive |
| **pdf2image** | MIT | PDF → image rendering (uses poppler) | ⚠️ Depends on poppler (GPL with exceptions). Review needed for bundling. Use as system dependency. |
| **Ghostscript** | AGPL-3.0 | Advanced compression, rendering | ❌ **AGPL — DO NOT embed**. Call as external CLI tool only, or find alternative. Consider using pikepdf compression instead. |
| **LibreOffice** | MPL-2.0 | PDF → DOCX/XLSX/PPTX conversion | ⚠️ Heavy dependency. Run as CLI in container. Tier 3 only. |
| **Tesseract** | Apache-2.0 | OCR engine | ✅ Permissive. Tier 3 only. |

> **License review action item**: Before production deployment, have legal review the use of pikepdf (MPL-2.0) and pdf2image's poppler dependency (GPL). Both should be fine as system-level dependencies called at runtime, but this needs confirmation.

### Infrastructure (Local Development)

| Technology | Purpose |
|-----------|---------|
| **Docker** | Containerized services |
| **Docker Compose** | Local orchestration |
| **MinIO** | S3-compatible object storage (local) |

### Infrastructure (Production)

| Technology | Purpose |
|-----------|---------|
| **Cloudflare R2** or **AWS S3** | Object storage |
| **Railway** / **Render** / **Fly.io** (initial) | App hosting (MVP) |
| **AWS ECS** / **GCP Cloud Run** (scale) | Container orchestration (growth) |
| **Cloudflare** | CDN, DDoS protection, DNS |

---

## 4. Communication Patterns

### Frontend ↔ Backend
- **REST API** (JSON over HTTPS) for all operations
- **Server-Sent Events (SSE)** for real-time job progress updates
  - Why SSE over WebSocket: simpler, works through proxies, unidirectional (progress only goes server→client), auto-reconnect built into EventSource API
- **Presigned URLs** for direct upload to object storage (large files)

### Backend ↔ Workers
- **Redis** as Celery message broker
- Workers read job config from PostgreSQL, download files from Object Storage
- Workers update job status in PostgreSQL and push progress via Redis pub/sub

### Storage Abstraction
All file operations go through a `StorageBackend` interface:
```
class StorageBackend(Protocol):
    async def upload(key, data, content_type) -> str
    async def download(key) -> bytes
    async def generate_presigned_url(key, expires_in) -> str
    async def delete(key) -> None
    async def exists(key) -> bool
```
Implementations: `MinIOStorage` (dev), `S3Storage` (prod), `R2Storage` (prod alternative).

---

## 5. Module Boundaries

The backend is organized into domain modules with clear boundaries:

```
backend/
├── app/
│   ├── core/           # Config, security, storage abstraction, shared utilities
│   ├── jobs/           # Job CRUD, state machine, progress tracking
│   ├── files/          # File metadata, upload/download endpoints, validation
│   ├── tools/          # Tool registry, tool-specific schemas & configs
│   ├── auth/           # Authentication, authorization (Tier 2)
│   ├── billing/        # Subscription management (Tier 2)
│   ├── api/            # API versioning, route aggregation
│   └── workers/        # Celery tasks, processing pipeline, tool handlers
```

**Rules for module boundaries:**
1. Modules communicate through service interfaces, not direct ORM queries
2. Each module owns its database tables
3. Cross-module references use IDs, not foreign objects
4. The `core` module is the only one that can be imported by all others

---

## 6. Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monolith vs microservices | Modular monolith | Faster development, simpler ops, sufficient for MVP scale |
| REST vs GraphQL | REST | Simpler for file operations, better caching, well-understood |
| SSE vs WebSocket | SSE for progress | Simpler, unidirectional, auto-reconnect, sufficient for updates |
| SQL vs NoSQL | PostgreSQL | ACID for job state, relational queries, JSON columns for flexibility |
| Direct upload vs proxy | Presigned URLs for large files, proxy for small | Avoids API server as bottleneck for large files |
| Session storage | Redis-backed | Fast, shared across instances, expirable |
| File deletion strategy | TTL-based with Celery Beat | Reliable, auditable, no external dependencies |
| Frontend state | Zustand | Lightweight, sufficient for tool UI state |
| Rendering strategy | SSG for tool pages, SSR for dynamic | SEO for tools, fast hydration, dynamic for user-specific pages |

---

## 7. Request Flow (Merge PDF Example)

```
1. User drops 2 PDF files onto the Merge tool page
2. Frontend validates files client-side (type, size)
3. Frontend calls POST /api/v1/jobs
   → Backend creates Job(status=PENDING, tool="merge")
   → Returns { job_id, upload_urls[] }
4. Frontend uploads files directly to Object Storage via presigned URLs
   → Progress tracked in UI
5. Frontend calls POST /api/v1/jobs/{job_id}/start
   → Backend validates all files exist in Object Storage
   → Updates Job(status=QUEUED)
   → Dispatches Celery task
6. Worker picks up task
   → Updates Job(status=PROCESSING)
   → Downloads inputs from Object Storage
   → Validates PDFs (structure, not malicious)
   → Merges PDFs using pypdf
   → Uploads result to Object Storage
   → Updates Job(status=COMPLETED, result_file=...)
7. Frontend polls SSE endpoint for progress
   → Receives COMPLETED event
   → Shows download button
8. User clicks download
   → Frontend calls GET /api/v1/jobs/{job_id}/download
   → Backend generates presigned URL (5-minute expiry)
   → Redirects user to presigned URL
9. Celery Beat cleanup task runs every 15 minutes
   → Finds jobs older than TTL
   → Deletes files from Object Storage
   → Updates Job(status=EXPIRED)
```

---

## 8. Scalability Path

| Phase | Scale | Architecture |
|-------|-------|--------------|
| **MVP** | ~100 concurrent users | Single API server + 2 Celery workers + 1 Redis + 1 PostgreSQL |
| **Growth** | ~1,000 concurrent users | 2 API servers behind LB + 4 workers + Redis Sentinel + PostgreSQL |
| **Scale** | ~10,000+ concurrent users | Auto-scaling API + auto-scaling workers + Redis Cluster + PostgreSQL replicas + CDN |
| **Enterprise** | Multi-tenant, multi-region | Potentially extract OCR/AI into separate services |
