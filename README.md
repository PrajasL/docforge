# DocForge — Online PDF Tools Platform

> **Status:** Phase 1 — Foundation (Local Dev Environment Setup Complete)  
> **Architecture:** Modular monolith + background workers  
> **Stack:** Next.js · FastAPI · Celery · Redis · PostgreSQL · MinIO/S3

---

## What is DocForge?

DocForge is a web-based PDF tools platform that lets users merge, split, compress, rotate, and transform PDF documents — fast, free, and private. Inspired by products like iLovePDF, but built from scratch with modern architecture and a privacy-first approach.

---

## Architecture Overview

```
User → Next.js Frontend → FastAPI API → Object Storage (MinIO/S3/R2)
                                      → Redis → Celery Worker → Result Storage → User
```

**Key design decisions:**
- **Modular monolith** — single codebase, domain-separated modules, no premature microservices
- **Async job processing** — every PDF operation is a background job with state tracking
- **Storage abstraction** — swap between MinIO (local), Cloudflare R2, or AWS S3 via config
- **Automatic cleanup** — all uploaded files are deleted after a configurable TTL
- **Security-first** — sandboxed processing, presigned URLs, no public storage buckets

---

## Technology Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui | MIT |
| Backend API | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 | MIT / PSF |
| Workers | Python, Celery 5, Redis 7 | BSD-3 |
| Database | PostgreSQL 16 | PostgreSQL License |
| PDF Processing | pypdf (BSD-3), pikepdf (MPL-2.0) | Permissive / Weak Copyleft |
| Local Storage | MinIO (S3-compatible) | AGPL (server) — fine for dev tooling |
| Infrastructure | Docker, Docker Compose | Apache-2.0 |

---

## Project Structure

```
PDF_PROJECT/
├── README.md                  ← You are here
├── BACKLOG.md                 ← Prioritized backlog
├── docs/
│   ├── product-requirements.md
│   ├── architecture.md
│   ├── database.md
│   ├── api-spec.md
│   ├── file-processing.md
│   ├── security.md
│   ├── testing-strategy.md
│   ├── deployment.md
│   ├── seo-architecture.md
│   ├── roadmap.md
│   ├── development-rules.md
│   └── project-status.md
├── backend/                   ← FastAPI + Celery (Phase 1)
│   ├── app/
│   │   ├── core/              # Config, security, storage
│   │   ├── jobs/              # Job CRUD, state machine
│   │   ├── files/             # File metadata, upload/download
│   │   ├── tools/             # Tool registry, schemas
│   │   ├── auth/              # Authentication (Phase 4)
│   │   ├── billing/           # Subscriptions (Phase 4)
│   │   ├── api/               # Route aggregation, versioning
│   │   └── workers/           # Celery tasks, tool handlers
│   ├── alembic/               # Database migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                  ← Next.js (Phase 1)
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   ├── components/        # Shared components
│   │   ├── lib/               # API client, utilities
│   │   └── styles/            # Global styles
│   ├── tests/
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml         ← Local development
├── docker-compose.test.yml    ← Test environment
└── .github/
    └── workflows/
        └── ci.yml
```

---

## Local Development

DocForge supports running either via **Docker Compose** (recommended when Docker is installed) or natively via **local processes**.

### 1. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```
*(On Windows PowerShell: `Copy-Item .env.example .env`)*

---

### Option A: Running with Docker Compose (All-in-One)

Prerequisite: Docker & Docker Compose installed.

```bash
# 1. Start all infrastructure and application services in background
docker compose up -d

# 2. Check service status
docker compose ps

# 3. View live logs
docker compose logs -f backend frontend

# 4. Run tests inside containers
docker compose exec backend pytest -v
docker compose exec frontend npm test

# 5. Stop all services
docker compose down
```

---

### Option B: Running Natively on Host

Prerequisites: Python 3.12+, Node.js 20+, npm.

#### Backend (FastAPI):
```bash
# 1. Set up Python virtual environment
python -m venv backend/venv

# 2. Activate virtual environment
# Windows:
backend\venv\Scripts\activate
# Linux/macOS:
source backend/venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements-dev.txt

# 5. Run database migrations
alembic -c backend/alembic.ini upgrade head

# 6. Start Celery worker (in a separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# 7. Start Celery Beat for scheduled cleanup (in a separate terminal)
celery -A app.workers.celery_app beat --loglevel=info

# 8. Run backend tests
pytest -v backend/tests

# 9. Start FastAPI development server (port 8000)
uvicorn app.main:app --app-dir backend --reload --port 8000
```

#### Automatic File Cleanup & Retention
DocForge implements automated temporary file expiration and cleanup:
- **Per-Job Expiration:** Jobs expire after `DEFAULT_JOB_TTL_SECONDS` (default: 7200 seconds / 2 hours).
- **Object Storage Cleanup:** A recurring Celery Beat task (`cleanup_expired_jobs_task`) executes every 15 minutes, finds expired jobs, securely deletes all input files and intermediate result objects from object storage, and transitions job records to `EXPIRED`.
- **Download Protection:** Access to expired result files is permanently blocked (HTTP 410 `FILE_EXPIRED`).
- **Production Cleanup:** In production (Cloudflare R2 or AWS S3), Celery Beat works alongside S3 Bucket Lifecycle Rules configured to automatically prune expired prefixes (`inputs/*`, `outputs/*`) as an additional safeguard.

#### Frontend (Next.js):
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install --legacy-peer-deps

# 3. Run frontend unit tests
npm test

# 4. Start Next.js development server (port 3000)
npm run dev
```

---

### Verifying Service Access & Health

Once services are running:
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Root**: [http://localhost:8000/](http://localhost:8000/)
- **Interactive Swagger Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **Liveness Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)
- **Readiness Probe**: [http://localhost:8000/health/ready](http://localhost:8000/health/ready) (probes PostgreSQL, Redis, and MinIO storage)
- **MinIO Console** *(via Docker)*: [http://localhost:9001](http://localhost:9001) (User: `minioadmin` / Pass: `minioadmin`)

---

## Documentation

| Document | Description |
|----------|-------------|
| [Product Requirements](docs/product-requirements.md) | Vision, user personas, feature tiers, success metrics |
| [Architecture](docs/architecture.md) | System design, tech stack, module boundaries, request flow |
| [Database](docs/database.md) | Entity relationships, state machine, indexing, retention |
| [API Specification](docs/api-spec.md) | REST endpoints, request/response schemas, error codes |
| [File Processing](docs/file-processing.md) | Processing pipeline, tool handler interface, validation |
| [Security](docs/security.md) | Threat model, upload protection, isolation, privacy |
| [Testing Strategy](docs/testing-strategy.md) | Test pyramid, CI pipeline, coverage targets |
| [Deployment](docs/deployment.md) | Docker setup, CI/CD, production platforms, monitoring |
| [SEO Architecture](docs/seo-architecture.md) | Programmatic SEO, structured data, performance |
| [Roadmap](docs/roadmap.md) | Development phases, milestones, timeline |
| [Development Rules](docs/development-rules.md) | Coding standards, git workflow, conventions |
| [Project Status](docs/project-status.md) | Current phase, pending decisions, blockers |
| [Backlog](BACKLOG.md) | All tasks organized by phase and priority |

---

## MVP Scope (Phase 1–3)

**4 tools:** Merge PDF, Split PDF, Compress PDF, Rotate PDF  
**Infrastructure:** Job system, file upload/download, auto-cleanup, rate limiting  
**Frontend:** Tool pages, drag-and-drop upload, real-time progress, download  
**SEO:** Per-tool landing pages with structured data  
**No auth required:** Anonymous usage with session-based access control

---

## Contributing

Development rules and conventions are documented in [docs/development-rules.md](docs/development-rules.md).

---

## License

Proprietary — All rights reserved.
