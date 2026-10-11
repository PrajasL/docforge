# Backlog

## How to Read This Backlog

> **Master Project Roadmap:** For the complete multi-phase architecture, detailed records of Parts 1–16, future tool specifications, risk matrix, and MVP launch checklist, refer to [PROJECT_ROADMAP.md](file:///c:/Users/praja/Documents/AI_PROJECTS/PDF_PROJECT/PROJECT_ROADMAP.md).

- Items are grouped by **phase** (aligned with the roadmap)
- Within each phase, items are ordered by **priority** (highest first)
- Each item has a **size estimate**: S (< 4h), M (4–8h), L (8–16h), XL (16h+)
- Labels: `core` `tool` `frontend` `backend` `worker` `infra` `security` `seo` `test` `docs`

---

## Phase 0 — Planning & Setup

- [x] Write product requirements document `docs` `core`
- [x] Write architecture document `docs` `core`
- [x] Write database schema document `docs` `core`
- [x] Write API specification `docs` `core`
- [x] Write file processing architecture `docs` `core`
- [x] Write security architecture `docs` `core`
- [x] Write testing strategy `docs` `core`
- [x] Write deployment strategy `docs` `core`
- [x] Write SEO architecture `docs` `core`
- [x] Write development roadmap `docs` `core`
- [x] Write development rules `docs` `core`
- [x] Review and approve plan with stakeholder `core` — **S**
- [x] Finalize product name and branding `core` — **S**
- [ ] Initialize Git repository `infra` — **S**
- [x] Set up monorepo directory structure `infra` — **S**
- [x] Create Docker Compose for local dev `infra` — **M** *(MinIO image updated to `cgr.dev/chainguard/minio` — official image removed Oct 2025)*
- [x] Set up GitHub Actions CI pipeline `infra` — **M**
- [x] Configure linting (ruff, mypy, eslint, prettier) `infra` — **M**

---

## Phase 1 — Foundation (Milestone 1: Merge PDF)

### Backend Core
- [x] FastAPI project scaffolding + config system `backend` `core` — **M**
- [x] PostgreSQL connection + SQLAlchemy setup `backend` `core` — **M**
- [x] Alembic migration setup `backend` `core` — **S**
- [x] Job model + enums `backend` `core` — **M**
- [x] Initial database migration `backend` `core` — **S**
- [x] Job state machine (transitions + validation) `backend` `core` — **M**
- [x] Storage abstraction interface `backend` `core` — **M**
- [x] MinIO storage implementation `backend` `core` — **M**
- [x] Presigned URL generation (upload + download) `backend` `core` — **M**
- [x] Session ID middleware (anonymous tracking) `backend` `core` — **S**
- [x] Request ID middleware `backend` `core` — **S**
- [x] Security headers middleware `backend` `security` — **S**
- [x] CORS configuration `backend` `security` — **S**
- [x] Docker services running & verified (Redis + MinIO healthy, integration tests all live) `infra` — **M**
- [ ] Rate limiting middleware (Redis) `backend` `security` — **M**
- [x] Standard error response handler `backend` `core` — **S**
- [x] Health check endpoints `backend` `core` — **S**

### Backend API Endpoints
- [x] POST /api/v1/jobs — create job `backend` — **M**
- [x] POST /api/v1/jobs/{id}/files/{id}/confirm `backend` — **S**
- [x] POST /api/v1/jobs/{id}/start `backend` — **M**
- [x] GET /api/v1/jobs/{id} — job status `backend` — **S**
- [x] GET /api/v1/jobs/{id}/progress — SSE stream `backend` — **M**
- [x] POST /api/v1/jobs/{id}/cancel `backend` — **S**
- [x] GET /api/v1/jobs/{id}/download `backend` — **M**
- [ ] GET /api/v1/tools — list tools `backend` — **S**
- [ ] GET /api/v1/tools/{id} — tool details `backend` — **S**

### Worker Infrastructure
- [x] Celery app configuration `worker` `core` — **M**
- [x] Base processing pipeline (fetch → validate → process → finalize) `worker` `core` — **L**
- [x] Tool handler interface / protocol `worker` `core` — **M**
- [x] Tool registry `worker` `core` — **S**
- [x] File validation (magic bytes, PDF structure) `worker` `security` — **M**
- [ ] Malicious PDF detection (log-only) `worker` `security` — **M**
- [x] Progress reporting via Redis pub/sub `worker` `core` — **M**
- [x] Temp file cleanup (per-job) `worker` `core` — **S**
- [x] Error handling + retry logic `worker` `core` — **M**
- [x] Celery Beat: expired file cleanup `worker` `core` — **M**
- [x] Celery Beat: expired job transition `worker` `core` — **S**

### First Tool: Merge PDF
- [x] Merge PDF handler implementation (pypdf) `worker` `tool` — **M**
- [x] Merge config schema + validation `backend` `tool` — **S**

### Frontend Core
- [x] Next.js project scaffolding `frontend` `core` — **M**
- [x] Tailwind CSS + shadcn/ui setup `frontend` `core` — **S**
- [x] Design system (colors, typography, spacing, dark mode) `frontend` `core` — **L**
- [x] Layout component (header, footer, nav) `frontend` `core` — **M**
- [x] API client with typed endpoints `frontend` `core` — **M**
- [x] File upload component (drag & drop dropzone) `frontend` `core` — **M**
- [x] Upload progress tracker `frontend` `core` — **M**
- [x] Job progress tracker (SSE stream + polling fallback) `frontend` `core` — **M**
- [x] Download result component `frontend` `core` — **S**
- [x] Error display components `frontend` `core` — **S**
- [x] Loading states and spinners `frontend` `core` — **S**

### Frontend Pages
- [x] Homepage (hero + tool cards + service health) `frontend` — **M**
- [x] Merge PDF tool page `frontend` `tool` — **L**
- [x] 404 & 500 error pages `frontend` — **S**

### Testing
- [x] Unit tests: job state machine `test` `backend` — **M**
- [x] Unit tests: merge handler `test` `worker` — **M**
- [x] Unit tests: file validation `test` `worker` — **M**
- [x] Unit tests: storage abstraction `test` `backend` — **S**
- [x] Integration test: full merge pipeline `test` — **L**
- [x] Frontend unit tests: Merge PDF page `test` `frontend` — **S**

---

## Phase 2 — Core Tools (Milestone 2)

### Tools
- [x] Split PDF handler `worker` `tool` — **L**
- [x] Split PDF config schema `backend` `tool` — **S**
- [x] Split PDF page `frontend` `tool` — **L**
- [x] Compress PDF handler (pikepdf) `worker` `tool` — **L**
- [x] Compress PDF config schema `backend` `tool` — **S**
- [x] Compress PDF page `frontend` `tool` — **L**
- [x] Rotate PDF handler `worker` `tool` — **M**
- [x] Rotate PDF config schema `backend` `tool` — **S**
- [x] Rotate PDF page `frontend` `tool` — **L**
- [x] Watermark PDF handler (reportlab + pypdf) `worker` `tool` — **M**
- [x] Watermark PDF config schema `backend` `tool` — **S**
- [x] Watermark PDF page `frontend` `tool` — **L**
- [x] Page Numbers PDF handler (reportlab + pypdf) `worker` `tool` — **M**
- [x] Page Numbers PDF config schema `backend` `tool` — **S**
- [x] Page Numbers PDF page `frontend` `tool` — **L**
- [x] Protect PDF handler (pypdf + cryptography AES-256) `worker` `tool` — **M**
- [x] Protect PDF config schema `backend` `tool` — **S**
- [x] Protect PDF page `frontend` `tool` — **L**
- [x] Unlock PDF handler (pypdf decryption) `worker` `tool` — **M**
- [x] Unlock PDF config schema `backend` `tool` — **S**
- [x] Unlock PDF page `frontend` `tool` — **L**
- [x] Extract Pages handler (pypdf) `worker` `tool` — **M**
- [x] Extract Pages config schema `backend` `tool` — **S**
- [x] Extract Pages page `frontend` `tool` — **L**
- [x] Organize PDF handler (pypdf) `worker` `tool` — **L**
- [x] Organize PDF config schema `backend` `tool` — **S**
- [x] Organize PDF page `frontend` `tool` — **L**
- [x] PDF to JPG handler (pypdfium2 + Pillow) `worker` `tool` — **L**
- [x] PDF to JPG config schema `backend` `tool` — **S**
- [x] PDF to JPG page `frontend` `tool` — **L**

### Shared UI
- [x] Unified shared tool header component (reusable layout across all 12 tools) `frontend` `core` — **M**
- [x] PDF page thumbnail previews `frontend` `core` — **L**
- [x] All Tools directory page `frontend` — **M**
- [x] Drag-and-drop page reordering `frontend` `core` — **M**

### Testing
- [x] Unit tests: split handler `test` — **M**
- [x] Integration test: split worker pipeline `test` — **L**
- [x] Frontend unit tests: Split PDF page `test` `frontend` — **S**
- [x] Unit tests: compress handler `test` — **M**
- [x] Integration test: compress worker pipeline `test` — **L**
- [x] Frontend unit tests: Compress PDF page `test` `frontend` — **S**
- [x] Unit tests: rotate handler `test` — **M**
- [x] Integration tests: rotate pipeline `test` — **L**
- [x] Frontend unit tests: Rotate PDF page `test` `frontend` — **S**
- [x] Unit tests: watermark handler `test` — **M**
- [x] Integration tests: watermark pipeline `test` — **L**
- [x] Frontend unit tests: Watermark PDF page `test` `frontend` — **S**
- [x] Unit tests: page numbers handler `test` — **M**
- [x] Integration tests: page numbers pipeline `test` — **L**
- [x] Frontend unit tests: Page Numbers PDF page `test` `frontend` — **S**
- [x] Unit tests: protect handler `test` — **M**
- [x] Integration tests: protect pipeline `test` — **L**
- [x] Frontend unit tests: Protect PDF page `test` `frontend` — **S**
- [x] Unit tests: unlock handler `test` — **M**
- [x] Integration tests: unlock pipeline `test` — **L**
- [x] Frontend unit tests: Unlock PDF page `test` `frontend` — **S**
- [x] Unit tests: extract pages handler `test` — **M**
- [x] Integration tests: extract pages pipeline `test` — **L**
- [x] Frontend unit tests: Extract Pages PDF page `test` `frontend` — **S**
- [x] Unit tests: organize handler `test` — **M**
- [x] Integration tests: organize pipeline `test` — **L**
- [x] Frontend unit tests: Organize PDF page `test` `frontend` — **S**
- [x] Unit tests: PDF to JPG handler `test` — **M**
- [x] Integration tests: PDF to JPG pipeline `test` — **L**
- [x] Frontend unit tests: PDF to JPG page `test` `frontend` — **S**
- [x] Browser E2E verification: PDF to JPG `test` — **M**
- [x] JPG to PDF tool handler implementation (`reportlab` + `Pillow`) `worker` `tool` — **L**
- [x] JPG to PDF frontend page (`/jpg-to-pdf`) with drag-and-drop reordering, layout options, and previews `frontend` `tool` — **L**
- [x] Unit tests: JPG to PDF handler (ordering, sizes, orientation, margins, resource limits) `test` — **M**
- [x] Integration tests: JPG to PDF live Celery worker pipeline `test` — **L**
- [x] Frontend unit tests: JPG to PDF page `test` `frontend` — **S**
- [x] Browser E2E verification: JPG to PDF `test` — **M**
- [x] Backend tests: SSE progress stream (`GET /api/v1/jobs/{id}/progress`, Redis Pub/Sub, heartbeats, disconnect cleanup, race conditions, monotonic progress, reconnects, DB heartbeat fallback) `test` `backend` — **M**
- [x] Frontend unit tests: All Tools directory page (`/tools` search, filter, empty state) `test` `frontend` — **S**
- [x] Frontend unit tests: Theme system (`ThemeProvider` & `ThemeToggle` persistence and system pref) `test` `frontend` — **S**
- [x] Frontend unit tests: `useJobProgress` SSE streaming hook with polling fallback, monotonic progress & reconnects `test` `frontend` — **S**
- [x] Browser E2E verification: Part 17 (Directory search/filter, theme toggling & persistence, SSE updates) `test` — **M**
- [x] Frontend unit tests: Part 18 SEO architecture (`tools-seo.test.ts` covering 12 tools uniqueness, canonical URLs, sitemap, robots, JSON-LD schemas, internal link mesh) `test` `frontend` — **S**
- [x] Browser E2E verification: Part 18 (SEO landing pages, How-To steps, FAQs accordion, related tools cross-linking) `test` — **M**


### Security Hardening
- [x] PDF.js security upgrade to latest stable (`pdfjs-dist@6.4.299`, resolve CVE-2024-4367 & engine overhaul) `security` `frontend` — **S**
- [x] Local PDF.js worker bundling (`/public/pdf.worker.min.mjs` matching 6.4.299, remove CDN) `security` `frontend` — **S**
- [x] Secure parser configuration (`enableXfa: false`, `isEvalSupported: false`, required DOM canvas) `security` `frontend` — **S**
- [x] Untrusted PDF regression tests `security` `test` — **S**
- [x] npm audit investigation (0 production vulnerabilities; documented 5 dev-dependencies `braces` advisories) `security` — **S**
- [x] PDF to JPG resource-limit audit (upload size, page count limits for 150/300 DPI, render dimension guards, 250 MB aggregate output limit) `security` `worker` — **S**
- [x] Unit tests: PDF to JPG resource limits, aggregate output limit, & failure cleanup `test` — **S**
- [x] Redis-backed atomic sliding-window rate limiting on job creation & upload tiers `security` `backend` — **M**
- [x] Safe client IP resolution with trusted reverse proxy configuration `security` `backend` — **S**
- [x] Upload guard: 0-byte file rejection, aggregate job size limit (250 MB), strict filename path-traversal sanitization `security` `backend` — **M**
- [x] ClamAV antivirus scanning integration (TCP INSTREAM, deterministic EICAR detection, fail-closed handling, infected object purging) `security` `backend` — **L**
- [x] Worker-level security verification guard (unscanned input rejection) `security` `worker` — **S**
- [x] Production security headers & CSP across FastAPI and Next.js (PDF.js worker and theme script compatible) `security` — **M**

---

## Phase 3 — Polish & Launch (Milestone 3)

### SEO (Parts 18 & 21 Complete)
- [x] Meta tags per tool page (unique titles, descriptions, canonical, OpenGraph, Twitter across 12 tools) `frontend` `seo` — **M**
- [x] JSON-LD structured data (Google-compliant `WebApplication`, `WebPage`, `HowTo`, `FAQPage` schemas matching visible content without fake reviews) `frontend` `seo` — **M**
- [x] Sitemap generation (dynamic `/sitemap.xml` with 16 canonical public routes including /privacy and /terms) `frontend` `seo` — **S**
- [x] robots.txt (dynamic `/robots.txt` disallowing `/api/` and `/_next/` with sitemap reference) `frontend` `seo` — **S**
- [x] Per-tool landing page copy (4-step How-To, truthful privacy cards, FAQs accordion, related tools mesh) `frontend` `seo` — **L**
- [ ] Open Graph images per tool `frontend` `seo` — **M**

### Polish (Part 21 Complete)
- [x] Responsive design audit + fixes (375px mobile viewport 0 horizontal overflow) `frontend` — **L**
- [ ] Micro-animations and transitions `frontend` — **M**
- [x] Dark mode support `frontend` — **M**
- [x] Accessibility audit (automated axe-core WCAG 2.1 AA audit reporting 0 violations across all 16 canonical routes in light and dark modes) `frontend` — **M**
- [x] Privacy policy page (`/privacy` with truthful 2h TTL, MinIO/PostgreSQL, ClamAV, zero 3rd-party APIs, Sentry scrubbing) `frontend` — **S**
- [x] Terms of service page (`/terms` with honest service guarantees, standard limitations, and customization placeholders) `frontend` — **S**
- [ ] About page `frontend` — **S**

### Infrastructure (Part 20 Complete)
- [x] Production Docker multi-stage setup & Compose (`docker-compose.prod.yml`, Caddy reverse proxy, resource limits, non-root users) `infra` — **L**
- [x] Cloudflare R2 / AWS S3 production storage integration (`S3StorageBackend` scoped-token fallback & presigned overrides) `infra` — **M**
- [x] Sentry error tracking with strict PII & zero-leak upload scrubber (`app/core/monitoring.py`) `infra` — **S**
- [x] Health checks & observability (`/health/live`, `/health/ready` probing DB, Redis, Storage, Celery, ClamAV) `infra` — **S**
- [x] Production stack dry-run verification (`verify_production_dryrun.py` end-to-end against local production stack with non-root users, S3 path, ClamAV EICAR catch, rate limit 429, log privacy audit) `infra` `test` — **M**
- [ ] Cloudflare CDN + DNS custom domain setup `infra` — **S**
- [ ] Google Search Console registration `seo` — **S**
- [ ] Analytics setup (Plausible/Umami) `infra` — **S**

### Quality (Part 21 Complete)
- [x] E2E tests (Playwright maintained suite covering all 12 tools, edge cases, security, UX, SEO, and accessibility) `test` — **L**
- [ ] Lighthouse performance audit `test` — **M**
- [x] Security header audit `security` — **S**
- [x] Rate limiting verification `security` — **S**
- [ ] Staging environment `infra` — **M**

---

## Phase 4 — Core Conversion & File Format Expansion

### Part 22 — PDF Repair Tool (Complete & Verified)
- [x] Backend handler: `RepairPDFHandler` with `pikepdf`/QPDF reconstruction & `pypdf` stream salvage fallback `backend` `tool` — **M**
- [x] Backend integration: register `repair` tool in registry and update Celery worker result metadata `backend` `worker` — **S**
- [x] Frontend route: `/repair-pdf` page with dropzone, status badges ("Structural Damage Repaired" vs "Structurally Sound"), and download button `frontend` `tool` — **M**
- [x] SEO & Discovery: `repair-pdf` in `tools-seo.ts`, 17 canonical routes in `sitemap.ts`, card in `/tools` and homepage `upcomingTools` `frontend` `seo` — **S**
- [x] Backend unit & integration tests (`test_repair_handler.py`, `test_repair_integration.py` passing 10/10) `test` `backend` — **M**
- [x] Frontend unit tests (`repair-pdf/page.test.tsx` passing 7/7) `test` `frontend` — **S**
- [x] E2E Playwright verification: Tool 13 in master suite verifying damaged xref reconstruction, browser download, and page count `test` — **M**

### Part 23 — PDF to Word (Next)
- [ ] PDF → Word (DOCX) layout extraction `tool` `backend` `frontend` — **XL**

---

## Phase 5+ — Future (Not Scheduled)

- [ ] User registration + login `backend` `frontend` — **XL**
- [ ] OAuth (Google, GitHub) `backend` — **L**
- [ ] Stripe billing integration `backend` — **XL**
- [ ] Delete Pages tool `tool` — **M**
- [ ] Word → PDF `tool` — **L**
- [ ] OCR `tool` — **XL**
- [ ] Public API + API keys `backend` — **XL**
- [ ] AI Summarization `tool` — **XL**
- [ ] Ask PDF `tool` — **XL**
- [ ] Workflows `backend` `frontend` — **XL**
- [ ] Team accounts `backend` — **XL**
