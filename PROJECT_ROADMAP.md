# DocForge Master Project Roadmap

> **Vision**: DocForge is a high-performance, private, 100% self-hosted alternative to iLovePDF and Smallpdf. All PDF and image transformations run locally within DocForge's own infrastructure without sending documents to third-party conversion APIs, using strictly permissive open-source libraries (BSD, MIT, Apache 2.0, MPL 2.0) with zero AGPL contamination.

---

## 1. Project Overview & Progress Summary

| Category | Status | Details |
|---|---|---|
| **Completed Parts** | 22 Parts | Architecture, Storage, Worker Pipeline, 13 Core PDF/Image Tools (including Part 22 Repair PDF), All Tools Directory, Theme System, Real-Time SSE Progress, Per-Tool SEO Architecture, Production Security, Production Deployment & Cloud Storage, End-to-End Testing, Accessibility & Legal Pages |
| **Active Tools** | 13 Tools | Merge, Split, Compress, Rotate, Watermark, Page Numbers, Protect, Unlock, Extract Pages, Organize, PDF to JPG, JPG to PDF, Repair PDF |
| **Backend Test Coverage** | 181 tests passing (100%) | Unit, state machine, handler, failure cleanup, live Celery/MinIO integration, Redis SSE, rate limiting, security headers, upload guard & ClamAV, production health/monitoring, and Repair PDF recovery tests |
| **Frontend Test Coverage** | 132 tests passing (100%) | Vitest across 20 test suites (including Repair PDF, legal pages, SEO, metadata, canonical, sitemap, robots, theme, and components) |
| **Browser E2E Verification** | Verified (3 Suites, 24 Scenarios) | Playwright test suites (`tests/e2e/run_all.py`): All 13 tools end-to-end (13/13), Edge cases & security (5/5), UX, SEO & Accessibility (6/6, **0 WCAG 2.1 AA axe-core violations across ALL 17 routes in light and dark modes**) |
| **Security & Compliance** | Hardened | Atomic Redis rate limiter, ClamAV INSTREAM malware scanning with EICAR detection, upload guards (0-byte rejection, path traversal prevention, aggregate limits), CSP/HSTS headers, truthful legal pages (/privacy, /terms), 0 production npm audit vulnerabilities |

---

## 2. Completed Parts (Parts 1–19)

All 19 parts listed below are fully implemented, verified, and operational in the codebase:


### Part 1 — Planning, Architecture & Requirements Specification
- **Status**: ✅ Complete
- **Delivered**: Complete documentation suite in `docs/`: Product Requirements Document (PRD), Architecture, Database Schema, API Specification, File Processing Pipeline, Security Architecture, Testing Strategy, Deployment Strategy, SEO Architecture, and Development Rules.
- **Verification**: 11 approved architecture documents defining system boundaries, data flows, and non-functional requirements.

### Part 2 — Monorepo & Local Development Infrastructure
- **Status**: ✅ Complete
- **Delivered**: Monorepo directory structure, Docker Compose configuration (`cgr.dev/chainguard/minio`, PostgreSQL 16, Redis 7), Python 3.13 FastAPI backend with async SQLAlchemy 2.0, Next.js 16 (App Router + Turbopack) frontend, Alembic migration setup, and health check endpoints.
- **Verification**: Health endpoints (`/health/live`, `/health/ready`), Docker container lifecycle validation, and clean startup.

### Part 3 — Storage Abstraction & Upload Infrastructure
- **Status**: ✅ Complete
- **Delivered**: `StorageBackend` abstraction interface, `S3StorageBackend` (MinIO/S3 compatible), date-partitioned storage keys (`inputs/YYYY/MM/DD/...`), presigned upload PUT URLs, direct API binary upload fallback, filename sanitization, SHA-256 calculation, and magic byte validation for PDFs.
- **Verification**: `test_storage.py` and `test_file_validation.py` passing against live MinIO.

### Part 4 — Job State Machine & Celery Worker Pipeline
- **Status**: ✅ Complete
- **Delivered**: SQLAlchemy `Job` model with strict state machine (`PENDING` → `UPLOADING` → `PROCESSING` → `COMPLETED` / `FAILED` / `CANCELLED`), Celery background worker setup with solo pool, Celery Beat scheduled tasks for automatic expired file and job cleanup, isolated per-job temporary workspace directories, and job TTL management.
- **Verification**: `test_job_model.py`, `test_jobs_api.py`, `test_celery_redis_integration.py`, and `test_workers_and_cleanup.py`.

### Part 5 — Merge PDF (Milestone 1 Core Tool)
- **Status**: ✅ Complete
- **Delivered**: `MergePDFHandler` using `pypdf` (BSD-3-Clause). Support for combining 2 to 20 PDF documents in user-specified sequence. DocForge homepage with tool cards and service health monitoring. Next.js tool page at `/merge` with drag-and-drop dropzone, file list reordering, progress tracking, and download button.
- **Verification**: 42 backend tests, 5 frontend tests, and `verify_ui_e2e.py` browser verification.

### Part 6 — Split PDF
- **Status**: ✅ Complete
- **Delivered**: `SplitPDFHandler` using `pypdf` and `zipfile`. Split modes: specific page ranges (e.g. `1-2, 3-5`) into separate PDF files or extracting every page into individual PDFs packaged into a ZIP archive. Next.js `/split` tool page with range input and real-time validation.
- **Verification**: 6 unit tests, 1 live worker integration test, and 7 frontend tests.

### Part 7 — Compress PDF
- **Status**: ✅ Complete
- **Delivered**: `CompressPDFHandler` using `pikepdf` (MPL 2.0) and `Pillow` (HPND). Deflate stream compression, object pruning, cross-reference stream compaction, and image downsampling. Three compression tiers (`recommended`, `balanced`, `maximum`). Negative savings prevention (preserves original document if output is larger). Responsive `/compress` page with savings badges.
- **Verification**: 6 unit tests, 1 live worker integration test, 7 frontend tests, and Edge browser verification.

### Part 8 — Rotate PDF
- **Status**: ✅ Complete
- **Delivered**: `RotatePDFHandler` using `pypdf`. Lossless rotation modifying page `/Rotate` dictionary attributes without recompressing streams or altering vector graphics. Supported angles: 90°, 180°, 270° clockwise. Scope: all pages or selective page ranges. Responsive `/rotate` page.
- **Verification**: 5 unit tests, 1 live worker integration test, 7 frontend tests, and Edge browser verification.

### Part 9 — Watermark PDF
- **Status**: ✅ Complete
- **Delivered**: `WatermarkPDFHandler` using `reportlab` (BSD) and `pypdf`. Dynamic text watermark rendering with configurable font size, rotation angle (-180° to 180°), opacity (alpha), text color, 9 cardinal positions, and selective page targeting. Responsive `/watermark` page.
- **Verification**: 5 unit tests, 1 live worker integration test, 7 frontend tests, and Edge browser verification.

### Part 10 — Page Numbers PDF
- **Status**: ✅ Complete
- **Delivered**: `PageNumbersPDFHandler` using `reportlab` and `pypdf`. Header and footer page numbering stamping. Formats: "Page X of Y", "X of Y", "X / Y", "X". Customizable starting page, margins, font size, color, 6 layout positions (top/bottom left/center/right), and selective page ranges. Responsive `/page-numbers` page.
- **Verification**: 6 unit tests, 1 live worker integration test, 7 frontend tests, and `verify_page_numbers_browser.py` Edge test.

### Part 11 — Protect PDF
- **Status**: ✅ Complete
- **Delivered**: `ProtectPDFHandler` using `pypdf` and `cryptography`. Standard AES-256 encryption. User password protection, password confirmation validation, show/hide password controls. Ephemeral Redis key storage for passwords with immediate deletion upon worker pickup (never stored in PostgreSQL or job config). Responsive `/protect` page.
- **Verification**: 4 unit tests, 1 live worker integration test, 6 frontend tests, and `verify_protect_browser.py` Edge test.

### Part 12 — Unlock PDF
- **Status**: ✅ Complete
- **Delivered**: `UnlockPDFHandler` using `pypdf`. Validates supplied password, decrypts document structure, and generates an unencrypted PDF that opens without a password. Does not attempt brute-forcing. Ephemeral Redis password exchange. Responsive `/unlock` page.
- **Verification**: 7 unit tests, 1 live worker integration test, 6 frontend tests, and `verify_unlock_browser.py` Edge test.

### Part 13 — Extract Pages
- **Status**: ✅ Complete
- **Delivered**: `ExtractPagesPDFHandler` using `pypdf`. Selective page extraction with range syntax (`1, 3-5, 8`), page count validation against document length, "extract all pages into one PDF" mode. Resolved compressed-object-stream page counting defect. Responsive `/extract-pages` page.
- **Verification**: 8 unit tests, 1 live worker integration test, 13 frontend tests, and `verify_extract_pages_browser.py` Edge test.

### Part 14 — Organize PDF & PDF.js Security Hardening
- **Status**: ✅ Complete
- **Delivered**: `OrganizePDFHandler` using `pypdf`. Visual page grid with real-time thumbnail rendering using locally bundled `pdfjs-dist@6.4.299` (`/public/pdf.worker.min.mjs`, `isEvalSupported: false`, `enableXfa: false`, zero CDN dependencies). Drag-and-drop page reordering, per-page 90° rotation, deletion, duplication, and undo history stack. Responsive `/organize-pdf` page.
- **Verification**: 7 unit tests, 1 live worker integration test, 11 frontend tests, and `verify_organize_browser.py` Edge test.

### Part 15 — PDF to JPG & Resource Limits Audit
- **Status**: ✅ Complete
- **Delivered**: `PdfToJpgPDFHandler` using `pypdfium2` (Apache 2.0 / BSD-3) and `Pillow`. Renders every page into high-quality JPEG images packaged into a ZIP archive. Standard (150 DPI) and high resolution (300 DPI) options, quality slider. Strict resource limits: 50 MB file size, 100 pages (150 DPI), 50 pages (300 DPI), 8,000 px / 36 MP per page bitmap guard, and 250 MB aggregate output limit with incremental disk checks and temp file cleanup. Responsive `/pdf-to-jpg` page.
- **Verification**: 15 unit tests, 1 live worker integration test, 7 frontend tests, and `verify_pdf_to_jpg_browser.py` Edge test.

### Part 16 — JPG to PDF
- **Status**: ✅ Complete
- **Delivered**: `JpgToPdfPDFHandler` using `reportlab` and `Pillow`. Multi-image JPEG upload (up to 50 images), visual thumbnail gallery, HTML5 drag-and-drop reordering, move earlier/later buttons, removal, orientation options (Auto, Portrait, Landscape), page sizes (Fit to image, A4, Letter), margins (None, Small - 18 pt, Normal - 36 pt), EXIF orientation normalization, and custom output filename. Resource limits: 25 MB per image, 50 files max, 10,000 px max dimension, 150 MP cumulative pixels, and 100 MB aggregate output PDF size with strict temporary file cleanup on success and failure. Responsive `/jpg-to-pdf` page and homepage card.
- **Verification**: 11 unit tests, 1 live worker integration test, 5 frontend tests, and `verify_jpg_to_pdf_browser.py` Edge test with regression checks across all 12 tool routes.

### Part 17 — All Tools Directory, Theme System & Real-Time Job Progress
- **Status**: ✅ Complete
- **Delivered**:
  - **All Tools Directory (`/tools`)**: Centralized directory with search across title, description, and keywords, category filtering pills (All, Organize, Optimize, Convert, Security), active tool counter, keyboard shortcut (`/`), responsive card grid with quick links, and empty state search reset.
  - **Dark and Light Theme System**: `ThemeProvider` and `ThemeToggle` with system preference detection, localStorage persistence, zero-FOUC inline script in `<head>`, and seamless light/dark styling applied across all 12 tool routes and homepage.
  - **Server-Sent Events Real-Time Progress**: `GET /api/v1/jobs/{id}/progress` streaming endpoint powered by Redis Pub/Sub, delivering instant worker progress updates, 15-second heartbeat comments, disconnect detection and resource cleanup, with automatic polling fallback in the frontend `useJobProgress` hook.
  - **Branded Error Pages**: Custom DocForge 404 (`not-found.tsx`), 500 (`error.tsx`), and global fatal error boundary (`global-error.tsx`).
- **Verification**: 11 backend SSE reliability tests (143 total backend passing), 16 frontend unit tests including monotonic progress & reconnect tests (107 total frontend passing across 16 test files), 0 TypeScript errors, 0 npm production vulnerabilities, clean Next.js build (17 routes), and Playwright/Edge E2E verification (`verify_part17_browser.py`) covering directory search, category filtering, theme toggling, SSE updates, and regression checks across all 12 tool routes.

---

### Part 18 — Per-Tool SEO Architecture & Landing Page Content
- **Status**: ✅ Complete & Audited
- **Delivered**:
  - **Per-Tool Landing Pages & Content**: Unique titles, meta descriptions, clear H1s, concise intros, 4-step How-To guides, truthful privacy/trust cards ("Dedicated Private Processing"), interactive FAQ accordions, and related tool internal linking meshes across all 12 PDF tools (`merge`, `split`, `compress`, `rotate`, `watermark`, `page-numbers`, `protect`, `unlock`, `extract-pages`, `organize-pdf`, `pdf-to-jpg`, `jpg-to-pdf`). Upload dropzones remain prominent above the fold.
  - **Truthful Content Standard**: Transparent disclosure that file processing occurs on DocForge's dedicated private worker pipeline (not falsely claiming client-device execution where backend workers are used). Clarified that Organize PDF thumbnails render client-side via bundled PDF.js worker while compilation executes on backend workers. Harmonized retention claims to the exact backend TTL of automatic 2-hour deletion. No duplicate boilerplate, no keyword stuffing, no fake reviews/ratings, and zero third-party cloud conversion APIs.
  - **Structured Data (JSON-LD)**: Schema markup with `@graph` containing `WebApplication` (genuine application info, price: 0, web platform, `operatingSystem: "All"`, `browserRequirements`), `WebPage` (linked to `WebSite`), `HowTo` (matching visible step text), and `FAQPage` (matching visible FAQ questions and answers). No fake `aggregateRating` or `review` entities; code documentation notes Google's restriction on rich result guarantees for How-To and FAQPage.
  - **Technical SEO**: Dynamic `sitemap.xml` (`src/app/sitemap.ts`) for canonical public pages, dynamic `robots.txt` (`src/app/robots.ts`) disallowing internal `/api/` and `/_next/`, configurable absolute canonical URLs based on `NEXT_PUBLIC_SITE_URL` (defaulting safely to `https://docforge.com` with console notification in production if unset). Documented `NEXT_PUBLIC_SITE_URL` in root `.env.example` and `frontend/.env.example`. Server component `layout.tsx` files for all 12 tools exporting Next.js `metadata`.
- **Verification**: 8 unit tests in `src/config/tools-seo.test.ts` (115 total frontend passing across 17 test suites, 143 backend passing), 0 TypeScript errors, 0 npm production vulnerabilities, clean Next.js build (17 routes including dynamic `/sitemap.xml` and `/robots.txt`), and Playwright / MS Edge browser E2E verification of landing content, FAQs, and internal links.

### Part 19 — Production Security, Rate Limiting & Upload Guard
- **Status**: ✅ Complete
- **Delivered**:
  - **Redis-Backed Atomic Rate Limiting**: Lua script sliding-window limiter protecting abuse-prone endpoints (`POST /api/v1/jobs` tier at 20 req/60s; upload tier at 60 req/60s; general tier at 120 req/60s). Returns HTTP 429 with `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers. Excludes Server-Sent Events (SSE) `/progress` and health probes to protect live users.
  - **Safe Client IP Resolution**: `resolve_client_ip` inspects socket peer and trusts `X-Forwarded-For` only when requests originate from explicitly configured `TRUSTED_PROXIES`.
  - **ClamAV Antivirus Scanner Pipeline**: Asynchronous ClamAV client (`app/core/scanner.py`) implementing TCP `INSTREAM` protocol without writing temporary files to host disk. Built-in standard EICAR test signature detection. Configurable fail-closed behavior (`CLAMAV_FAIL_CLOSED=True` / 503 `SCANNER_UNAVAILABLE`). Immediate purge of malicious objects from storage upon detection.
  - **Upload Guard & Boundary Validation**: Rejection of 0-byte/empty files at job creation and upload. Strict filename sanitization preventing directory traversal (`..`, `\x00`, control characters). Total aggregate job size limit enforcement (`MAX_AGGREGATE_JOB_SIZE_MB = 250`). Worker-level security verification guard ensuring unscanned files never execute.
  - **Security Headers & CSP**: Applied Content-Security-Policy (CSP), HSTS (`Strict-Transport-Security: max-age=31536000`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy` across both FastAPI backend middleware and Next.js frontend App Router. CSP fully verified compatible with inline theme script, local PDF.js workers (`worker-src 'self' blob:`), and Turbopack.
  - **Docker Compose & Environments**: Added `clamav` container (`clamav/clamav:latest`, port 3310, `clamav_data` volume) to `docker-compose.yml`, updated `.env.example`.
- **Verification**: 24 dedicated security, rate limiting, and antivirus tests (161 total backend tests passing, 115 frontend Vitest tests passing), 0 TypeScript errors, 0 npm production vulnerabilities, clean production build (19 routes), and real browser E2E verification of `/merge` and `/tools` confirming 0 CSP violations and 0 console errors.

---

## 3. Prioritized Roadmap for Remaining Work

The remaining roadmap is divided into structured phases balancing launch essentials with advanced feature expansions:

```
Phase 2.5: Shared Platform Polish & Directory (Parts 17–18)       ← COMPLETED
Phase 3.0: Launch Readiness, Security & Production (Parts 19–20)   ← PARTS 19 & 20 COMPLETE; PART 21 NEXT
Phase 4.0: Core Conversion & Utility Suite    (Parts 22–27)
Phase 5.0: Advanced Editing & Signatures     (Parts 28–32)
Phase 6.0: Accounts, Cloud & Monetization    (Parts 33–36)
```

---

### Phase 3.0 — Launch Readiness, Security Hardening & Production Deployment

#### Part 19 — Production Security, Rate Limiting & Upload Guard
- **Status**: ✅ Complete

#### Part 20 — Production Deployment & Cloud Storage Migration (Launch Candidate)
- **Status**: ✅ Complete & Verified (Dry-Run Validated)
- **Delivered**:
  - **Multi-Stage Production Dockerfiles**:
    - Backend (`backend/Dockerfile`): Minimal `python:3.12-slim` builder and runner stages, pinned boto3/botocore/aiobotocore/aioboto3 dependencies, non-root user `appuser` (UID 10001), healthcheck via `/health/live`, `curl` installation, multi-worker uvicorn command.
    - Frontend (`frontend/Dockerfile`): `node:22-alpine` multi-stage build (`deps` -> `builder` -> `runner`), Next.js standalone output (`output: "standalone"` in `next.config.ts`), non-root user `nextjs` (UID 1001), healthcheck via `/api/health`.
  - **Production Storage Abstraction (Cloudflare R2 & AWS S3)**:
    - Extended `S3StorageBackend` in `backend/app/core/storage.py` and `backend/app/core/config.py` with `STORAGE_PROVIDER` (`r2`, `s3`, `minio`), `STORAGE_PUBLIC_DOMAIN`, and `STORAGE_PRESIGNED_ENDPOINT_OVERRIDE`.
    - Resilient health check supporting Cloudflare R2 scoped per-bucket API tokens (catches 403 / AccessDenied and verifies via `head_bucket`).
    - Resilient `ensure_buckets_exist` tolerant of production restricted token permissions.
    - Presigned URL host rewrite mechanism for seamless container-to-browser endpoint mapping.
  - **Telemetry & Error Tracking (Sentry Integration)**:
    - Created `backend/app/core/monitoring.py` integrated into FastAPI lifespan and Celery worker startup via optional `SENTRY_DSN`.
    - Enforced zero-leak data protection guarantee: scrubs request headers (`Authorization`, `Cookie`, `X-Session-Id`), scrubs request payloads (drops `multipart/form-data`, `application/pdf`, and binary blobs to `[FILTERED_UPLOAD_PAYLOAD]`), scrubs dictionary fields containing `password`, `secret`, `token`, and sanitizes S3 query params (`X-Amz-Signature`, etc.) from URLs and breadcrumbs.
  - **Comprehensive Health & Observability Endpoints**:
    - `/health` & `/health/live`: Fast process liveness probes (HTTP 200) for container orchestrators without querying downstream services.
    - `/health/ready`: Full dependency readiness check concurrently probing PostgreSQL, Redis, Storage (R2/S3/MinIO), Celery workers (`ping` via Redis broker), and ClamAV daemon. Clearly distinguishes application process health from downstream dependency health with HTTP 200 (ready/operational) vs HTTP 503 (core dependency offline or fail-closed scanner down).
  - **Production Docker Compose & Edge Layer**:
    - `docker-compose.prod.yml`: Standard Docker Compose configuration (no Swarm dependencies), internal isolated networks (`internal-net`, `edge-net`), PostgreSQL/Redis/ClamAV host ports closed from host exposure, resource limits (`deploy.resources.limits` & `reservations`) across all containers, Celery worker (4 concurrency) and Celery Beat scheduler for automated cleanup.
    - Reverse Proxy: Edge reverse proxy setup with Caddy (`docker/Caddyfile`) for automated HTTPS/TLS, Brotli/Gzip/Zstd compression, and security headers, alongside alternative production Nginx config (`docker/nginx.conf`).
  - **Deployment Documentation & Environments**:
    - Created `.env.production.example` template with production defaults.
    - Authored `docs/deployment-guide.md` with complete architecture diagram, Cloudflare R2 setup, Sentry integration, deployment steps, Alembic database migrations, backup & recovery scripts, and zero-downtime rollback procedures.
- **Verification (Local Production Dry-Run)**:
  - **Production Stack Dry-Run (`verify_production_dryrun.py`)**:
    - All 9 production containers healthy: `docforge-prod-backend`, `docforge-prod-frontend`, `docforge-prod-worker`, `docforge-prod-beat`, `docforge-prod-postgres`, `docforge-prod-redis`, `docforge-prod-storage`, `docforge-prod-clamav`, `docforge-prod-proxy`.
    - Non-root users verified: backend & worker `uid=10001(appuser) gid=10001(appgroup)`, frontend `uid=1001(nextjs) gid=1001(nodejs)`.
    - Liveness (`/health/live`) and readiness (`/health/ready`) probes reported HTTP 200 with all 5 dependencies connected (DB, Redis, S3, Celery, ClamAV).
    - Harmless PDF end-to-end processing (Rotate 90) passed: presigned S3 upload, ClamAV scan, Celery worker execution (0.5s), presigned download, verified 90° rotation with `pikepdf`.
    - ClamAV malware rejection: caught EICAR test signature, returned HTTP 400 `MALWARE_DETECTED`, purged infected object from storage.
    - Rate limiting: Redis-backed sliding window triggered HTTP 429 Too Many Requests with `Retry-After: 58s`.
    - Real-time SSE stream: `GET /api/v1/jobs/{id}/progress` streamed `text/event-stream` with HTTP 200.
    - Sentry scrubbing: verified redaction of synthetic sensitive payloads (headers, passwords, secrets, PDF contents, presigned query parameters).
    - Log privacy audit: confirmed zero passwords, tokens, presigned signatures, or raw PDF contents in container logs.
  - **Cloud Storage & External Status**:
    - S3-compatible path verified against local S3 container via Caddy proxy; live Cloudflare R2 and production domain/SSL require a real cloud account and production credentials.
  - **Automated Test Suites**:
    - Backend: 171 tests passing (161 core + 10 production health & monitoring tests).
    - Frontend: 119 tests passing across 18 Vitest suites.
    - TypeScript: 0 errors (`npx tsc --noEmit`).
    - Next.js build: clean standalone build across 20 routes.
    - Security audits: `npm audit --omit=dev` 0 vulnerabilities; 5 known development-dependency advisories documented.
- **Remaining Risks & Mitigations**:
  - *Cloudflare R2 Bucket Lifecycle*: Users must configure 24-hour expiration lifecycle rules in Cloudflare dashboard to ensure deletion if worker cleanup is interrupted (documented in `docs/deployment-guide.md`).
  - *ClamAV Cold Start in CI*: ClamAV database initialization can take 60–90s; container health check configured with 60s `start_period`.

#### Part 21 — End-to-End Testing, Accessibility & Legal Pages
- **Status**: ✅ Complete & Verified
- **Delivered**:
  - **Preliminary Safety Check & Volume Isolation**: Verified development Docker named volumes (`pdf_project_postgres_data`, `pdf_project_redis_data`, `pdf_project_minio_data`) are completely isolated from production. Hardened `docker-compose.prod.yml` with explicit project name (`name: docforge-prod`). Verified root `.gitignore` ignores all `.env*.local` files without any exposed credentials.
  - **Accessibility Conformance (WCAG 2.1 AA Audit)**:
    - Scanned all 16 canonical public routes (`/`, `/tools`, `/privacy`, `/terms`, `/merge`, `/split`, `/compress`, `/rotate`, `/watermark`, `/page-numbers`, `/protect`, `/unlock`, `/extract-pages`, `/organize-pdf`, `/pdf-to-jpg`, `/jpg-to-pdf`).
    - Added explicit `aria-label` tags to hidden file inputs across all 12 tools.
    - Repaired dark and light mode color contrast ratios across action buttons, tool cards, error pages, and footers to strictly exceed 4.5:1.
    - Automated axe-core browser audit verified **0 WCAG 2.1 AA violations across all 16 routes in both light and dark modes**.
  - **Truthful Legal Pages (`/privacy` & `/terms`)**:
    - Built accessible, responsive legal pages with table of contents navigation, security architecture disclosures, and print styles.
    - Truthfully disclosed dedicated private worker processing (zero 3rd-party conversion APIs), 2-hour automatic TTL purge, local ClamAV scanning, MinIO/PostgreSQL storage, and Sentry zero-leak scrubbing.
    - Included clear deployer customization placeholders (jurisdiction, governing law, entity name) without inventing fictitious legal entities.
    - Updated `sitemap.ts` (now 16 canonical routes) and footer navigation.
  - **Comprehensive Playwright E2E Suite (`tests/e2e/`)**:
    - Built isolated `E2EFixturesManager` generating dynamic valid PDFs, multi-page PDFs, encrypted PDFs, JPG fixtures, corrupted files, and standard EICAR test signatures.
    - Built master orchestrator (`tests/e2e/run_all.py`) and 3 execution suites:
      - **Suite 1 (`test_all_12_tools.py`)**: 12/12 tools verified end-to-end (upload, configure, worker execution, download, and file integrity check with `pypdf`/`zipfile`/`Pillow`).
      - **Suite 2 (`test_edge_cases_security.py`)**: Non-PDF upload rejection, corrupted file graceful handling, encrypted PDF rejection on non-unlock tools, ClamAV malware rejection of EICAR with HTTP 400 `MALWARE_DETECTED`, and rate limit 80-request burst stability (5/5 passed).
      - **Suite 3 (`test_ux_seo_accessibility.py`)**: Theme persistence across page loads, header/footer navigation, 375px mobile responsive layout (0 horizontal overflow), robots.txt & sitemap.xml validation with all 16 URLs, canonical tags, and automated axe-core WCAG 2.1 AA audit (0 violations on all 16 routes) (6/6 passed).
- **Verification**:
  - 171 backend tests passing (100%).
  - 125 frontend Vitest tests passing across 19 suites (100%).
  - 0 TypeScript errors (`npx tsc --noEmit`).
  - Next.js standalone production build clean (22 routes).
  - 0 production npm audit vulnerabilities (`npm audit --omit=dev`).
  - All 3 Playwright E2E test suites passed (23 scenarios, 81.05s).

---

### Phase 4.0 — Core Conversion & File Format Expansion

#### Part 22 — PDF Repair Tool (`/repair-pdf`)
- **Status**: ✅ Complete & Verified
- **Delivered**:
  - **Repair Engine (`RepairPDFHandler`)**:
    - Low-level structural recovery using `pikepdf` (MPL 2.0) and QPDF (Apache 2.0) with automatic fallback to lenient stream salvage via `pypdf` (BSD-3-Clause). Zero AGPL dependencies.
    - Successfully recovers damaged cross-reference (`xref`) tables, corrupted `startxref` offsets, broken object streams, missing `%%EOF` markers, and malformed trailer dictionaries.
    - Preserves page content, dimensions (e.g. US Letter, A4), rotations, and document metadata where recovery permits.
    - Saves recovered document to a completely fresh PDF file; never overwrites original uploads.
    - Clear distinction between repaired damaged documents (`repaired: true`, status badge "Structural Damage Repaired") and already sound documents (`repaired: false`, status badge "Structurally Sound (Verified)").
    - Gracefully rejects password-protected PDFs (`PDF_ENCRYPTED`), empty files (`EMPTY_FILE`), empty page trees (`EMPTY_DOCUMENT`), and severely destroyed garbage (`UNRECOVERABLE_PDF`).
  - **Interactive Frontend (`/repair-pdf`)**:
    - Next.js interactive route with drag-and-drop dropzone, file selection card, upload/processing progress indicator, completed state with recovery badges, page count recovery summary, and download button.
    - SEO landing architecture (`tools-seo.ts` with 172-char meta description, 4-step How-To, FAQs, schemas).
    - Integrated into All Tools directory (`/tools` under "Optimize" category) and Homepage `upcomingTools`.
    - Dynamic `sitemap.ts` updated to 17 canonical routes.
  - **Comprehensive Verification**:
    - Backend: 9 handler unit tests (`test_repair_handler.py`) + 1 live Celery worker integration test (`test_repair_integration.py`).
    - Frontend: 7 Vitest unit tests (`repair-pdf/page.test.tsx`) + SEO suite tests.
    - Master E2E: Real Playwright E2E test verifying damaged xref recovery, browser download, and page integrity verification. 0 axe-core WCAG 2.1 AA violations.
- **Dependencies**: Part 21.

#### Part 23 — PDF to Word (DOCX) Conversion (`/pdf-to-word`)
- **Status**: 🔲 Planned (Next Step — Do Not Start Yet)
- **Scope**:
  - High-fidelity layout, paragraph, table, and font extraction into Microsoft Word (.docx) format using permissive Python libraries (`pdf2docx`).
  - Conversion progress tracking, downloadable DOCX output.
- **Dependencies**: Part 22.
- **Technical Risks**: High. Complex multi-column layouts, overlapping text, and non-standard font encodings.

#### Part 24 — Word to PDF (DOCX to PDF) Conversion (`/word-to-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Headless LibreOffice CLI (`soffice --headless --convert-to pdf`) containerized inside worker.
  - Converts `.doc` and `.docx` into standard PDF documents.
- **Dependencies**: Part 23.
- **Technical Risks**: High. Headless LibreOffice memory footprint and font availability in Docker containers.

#### Part 25 — OCR PDF (Searchable PDF) (`/ocr-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Optical Character Recognition on scanned PDFs and image-only documents using Tesseract OCR (`pytesseract` / `ocrmypdf`).
  - Generates invisible searchable text layer behind bitmap scans.
  - Multi-language dictionary support.
- **Dependencies**: Part 20.
- **Technical Risks**: High. High CPU/memory consumption; requires strict per-job timeout and page bounds.

#### Part 26 — PDF to Excel (XLSX) & Excel to PDF (`/pdf-to-excel`, `/excel-to-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Table detection and spreadsheet extraction using `pdfplumber` / LibreOffice headless.
  - Excel `.xlsx` to PDF conversion.
- **Dependencies**: Part 20.
- **Technical Risks**: Medium. Borderless tables and irregular merged cells.

#### Part 26 — PDF to PowerPoint (PPTX) & PPTX to PDF (`/pdf-to-powerpoint`, `/powerpoint-to-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Slide conversion and presentation rendering using LibreOffice headless.
- **Dependencies**: Part 20.
- **Technical Risks**: Medium. Slide layout scaling and aspect ratios.

#### Part 27 — PDF/A Archival Conversion (`/pdf-to-pdfa`)
- **Status**: 🔲 Planned
- **Scope**:
  - Convert standard PDFs into ISO 19005-compliant archival formats (PDF/A-1b, PDF/A-2b) using `pikepdf` / Ghostscript compliance profiles.
  - Font embedding and color space normalization.
- **Dependencies**: Part 20.
- **Technical Risks**: Medium. Missing embedded fonts in user uploads.

---

### Phase 5.0 — Advanced Editing, Redaction & Signatures

#### Part 28 — Sign PDF (`/sign-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Frontend canvas for signature drawing, initials typing, or PNG signature upload.
  - Visual signature placement on PDF pages with draggable, resizable signature boxes.
  - Stamping signature into document using ReportLab / pypdf.
- **Dependencies**: Part 20.
- **Technical Risks**: Medium. Coordinate scaling between browser viewport and PDF point system.

#### Part 29 — Redact PDF (`/redact-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - True irreversible text and visual redaction: permanently removes underlying text glyphs, vector shapes, and bitmap areas from content streams (not merely drawing black overlays).
  - Search-and-redact capability for sensitive terms (SSN, emails, credit cards).
- **Dependencies**: Part 20.
- **Technical Risks**: High. Ensuring complete removal from compressed object streams and xref dictionaries.

#### Part 30 — Compare PDF (`/compare-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Visual and textual side-by-side comparison of two PDF revisions.
  - Overlay diff rendering highlighting added, deleted, or shifted content.
- **Dependencies**: Part 20.
- **Technical Risks**: Medium. Alignment of slightly shifted pages.

#### Part 31 — Crop PDF (`/crop-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Interactive visual cropping box on page previews.
  - Applies `/CropBox` and `/MediaBox` updates across selected or all pages.
- **Dependencies**: Part 20.
- **Technical Risks**: Low. Simple bounding box dictionary math.

#### Part 32 — Fill & Flatten Forms (`/fill-pdf`)
- **Status**: 🔲 Planned
- **Scope**:
  - Detect and render PDF AcroForm fields (text fields, checkboxes, dropdowns).
  - Save completed form values and flatten into read-only document.
- **Dependencies**: Part 20.
- **Technical Risks**: Medium. Complex XFA dynamic forms vs static AcroForms.

---

### Phase 6.0 — User Accounts, Cloud Integrations & Monetization

#### Part 33 — User Authentication & Dashboard
- **Status**: 🔲 Planned
- **Scope**:
  - User registration, login, email verification, password reset.
  - OAuth 2.0 (Google, GitHub).
  - User dashboard showing conversion history within TTL and favorite tools.
- **Dependencies**: Part 20.
- **Technical Risks**: Low. Standard JWT authentication with refresh token rotation.

#### Part 34 — Cloud Storage Integrations (Google Drive & Dropbox)
- **Status**: 🔲 Planned
- **Scope**:
  - Direct import from Google Drive and Dropbox file pickers.
  - Save converted files directly back to connected cloud storage accounts.
- **Dependencies**: Part 33.
- **Technical Risks**: Low. Standard OAuth access tokens and drive APIs.

#### Part 35 — Stripe Monetization & Pro Subscriptions
- **Status**: 🔲 Planned
- **Scope**:
  - Stripe Checkout and Customer Portal integration.
  - Pro Tier: Increased file size limits (200 MB), unlimited batch uploads, priority Celery worker queue, extended file retention (24h).
  - Free Tier: Current anonymous limits (25–50 MB, 2h TTL).
- **Dependencies**: Part 33.
- **Technical Risks**: Medium. Webhook idempotency and subscription state synchronization.

#### Part 36 — Multi-Tool Workflows (Tool Chaining)
- **Status**: 🔲 Planned
- **Scope**:
  - Chain consecutive operations without re-downloading and re-uploading (e.g. Unlock → Organize → Compress → Download).
- **Dependencies**: Part 33.
- **Technical Risks**: Medium. Coordinating temporary storage keys across chained Celery jobs.

---

## 4. Dependencies & Technical Risk Matrix

| Risk / Dependency | Impact | Mitigation Strategy |
|---|---|---|
| **AGPL License Contamination** | Severe | Strict prohibition of AGPL libraries (e.g. Ghostscript, PyMuPDF, pdf2image GPL). Use BSD/MIT/MPL libraries exclusively (`pypdf`, `pikepdf`, `pypdfium2`, `reportlab`, `Pillow`). |
| **Worker Memory Exhaustion (OOM)** | High | Enforce strict per-tool upload size, page count, dimension, and aggregate output limits *before* and *during* processing. Never load entire files in memory; stream incrementally to disk. |
| **Untrusted File Exploits** | High | Magic byte verification, strict extension whitelisting, non-executable storage permissions, isolated Docker containers, locally bundled hardened `pdfjs-dist@6.4.299` with `isEvalSupported: false`. |
| **Large Conversion Engines (LibreOffice)** | Medium | Run dedicated LibreOffice conversion worker containers separate from fast PDF manipulation workers to isolate memory leaks and process crashes. |
| **Object Storage Cost & Data Leaks** | Medium | Automated Celery Beat TTL cleanup (2-hour default) unlinks all input and output files. Presigned URLs expire in 15 minutes. |

---

## 5. Launch-Readiness Checklist (MVP Release)

The following criteria define public launch readiness for DocForge v1.0:

- [x] **12 Core PDF/Image Tools Functional**: Merge, Split, Compress, Rotate, Watermark, Page Numbers, Protect, Unlock, Extract Pages, Organize, PDF to JPG, JPG to PDF.
- [x] **Zero AGPL Dependencies**: All libraries commercially safe under MIT, BSD, Apache 2.0, or MPL 2.0.
- [x] **PDF.js Security Hardened**: Latest stable `pdfjs-dist@6.4.299` bundled locally; eval and scripting disabled.
- [x] **Automated Test Coverage**: 100% pass rate across 143 backend tests, 107 frontend tests (16 test suites), and Playwright browser E2E tests.
- [x] **Resource Limits Enforced**: Strict guards preventing OOM crashes across all tools.
- [x] **All Tools Directory (`/tools`)**: Central directory with search and categorization (*Part 17*).
- [x] **Dark/Light Theme Toggle**: Polished UI with persistent user preference (*Part 17*).
- [x] **Real-Time Progress (SSE)**: Server-Sent Events stream replacing polling (*Part 17*).
- [ ] **SEO Infrastructure**: Per-tool metadata, JSON-LD schemas, sitemap.xml, robots.txt (*Part 18*).
- [ ] **Landing Page Content**: Clear how-to guides and technical FAQs per tool (*Part 18*).
- [ ] **Security Hardening**: Redis-backed rate limiting middleware and strict CSP headers (*Part 19*).
- [ ] **Legal & Informational Pages**: Privacy Policy, Terms of Service, About (*Part 18/20*).
- [ ] **Production Deployment Config**: Production multi-stage Docker Compose, Cloudflare R2 / S3 setup (*Part 20*).
- [ ] **Error Monitoring**: Sentry integration for real-time exception tracking (*Part 19/20*).

---

## 6. Recommended Next Development Task

### **Part 18 — Per-Tool SEO Architecture & Landing Page Content**
- **Objective**: Implement comprehensive search engine optimization and user guidance for all 12+ DocForge tools.
- **Deliverables**:
  1. Per-tool metadata (title, description, canonical, OpenGraph, Twitter).
  2. JSON-LD structured data schemas (`SoftwareApplication`, `HowTo`, `FAQPage`).
  3. Educational landing page sections (step-by-step how-to, technical specifications, privacy & security FAQs).
  4. Next.js dynamic `sitemap.xml` and `robots.txt` generation.
- **Estimated Effort**: 6–8 hours.
- **Why this next**: With the tools directory, theme system, and real-time SSE progress complete, SEO architecture and landing page content provide indexability and educational context for public discovery.
