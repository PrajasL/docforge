# Development Roadmap

## 1. Development Phases Overview

```
Phase 0: Planning & Setup          ← YOU ARE HERE
Phase 1: Foundation (Milestone 1)
Phase 2: Core Tools (Milestone 2)
Phase 3: Polish & Launch (Milestone 3)
Phase 4: Users & Monetization
Phase 5: Conversion Tools
Phase 6: Advanced Tools
Phase 7: AI & Enterprise
```

---

## 2. Phase 0 — Planning & Setup (Week 1)

**Goal:** Finalize architecture, set up repository and development environment.

| Task | Status | Effort |
|------|--------|--------|
| Complete planning documents | ✅ Done | — |
| Review and approve plan | ⬜ Pending | — |
| Finalize branding (name, domain) | ⬜ Pending | — |
| Set up Git repository | ⬜ Pending | 1h |
| Set up monorepo structure | ⬜ Pending | 2h |
| Create Docker Compose for local dev | ⬜ Pending | 4h |
| Configure CI pipeline (GitHub Actions) | ⬜ Pending | 4h |
| Set up linting and formatting | ⬜ Pending | 2h |

**Exit criteria:** `docker compose up` starts all services, CI runs lint checks.

---

## 3. Phase 1 — Foundation (Weeks 2–4)

**Goal:** Build the reusable job processing infrastructure. First working tool: **Merge PDF**.

### Milestone 1: "Upload → Merge → Download"

The end-to-end flow that proves the entire architecture works:

> User uploads two PDFs → system creates a job → worker merges the PDFs → result is stored → secure download is provided → temporary files are automatically deleted.

| Task | Layer | Effort |
|------|-------|--------|
| **Backend: Core infrastructure** | | |
| FastAPI project setup + config | Backend | 4h |
| Database models (Job, File) + Alembic setup | Backend | 6h |
| Storage abstraction (MinIO/S3 interface) | Backend | 6h |
| Presigned URL generation | Backend | 4h |
| Job state machine + transitions | Backend | 6h |
| Celery setup + base task pipeline | Worker | 8h |
| **Backend: Merge tool** | | |
| Tool registry + handler interface | Backend | 4h |
| Merge PDF handler (pypdf) | Worker | 4h |
| File validation (magic bytes, PDF structure) | Worker | 4h |
| **Backend: API endpoints** | | |
| POST /api/v1/jobs (create job) | API | 4h |
| POST /api/v1/jobs/{id}/files/{id}/confirm | API | 2h |
| POST /api/v1/jobs/{id}/start | API | 3h |
| GET /api/v1/jobs/{id} (status) | API | 2h |
| GET /api/v1/jobs/{id}/progress (SSE) | API | 4h |
| GET /api/v1/files/{id}/download | API | 3h |
| GET /api/v1/tools | API | 2h |
| Rate limiting middleware | API | 4h |
| Error handling middleware | API | 3h |
| **Backend: Cleanup** | | |
| Celery Beat: file cleanup task | Worker | 4h |
| Celery Beat: job expiration task | Worker | 2h |
| **Frontend: Core infrastructure** | | |
| Next.js project setup + Tailwind + shadcn/ui | Frontend | 4h |
| Design system (colors, typography, layout) | Frontend | 6h |
| API client (typed, error handling) | Frontend | 4h |
| File upload component (drag-and-drop) | Frontend | 6h |
| Upload progress tracking | Frontend | 4h |
| Job progress tracker (SSE client) | Frontend | 4h |
| Download result component | Frontend | 2h |
| **Frontend: Merge tool page** | | |
| Merge PDF page (upload, reorder, merge) | Frontend | 8h |
| Homepage (hero + tool cards) | Frontend | 6h |
| **Testing** | | |
| Unit tests: job state machine | Test | 3h |
| Unit tests: merge handler | Test | 3h |
| Integration test: full merge pipeline | Test | 6h |
| **Total estimated effort** | | **~140h** |

**Exit criteria:**
- Upload 2 PDFs via browser → get merged PDF download
- Files auto-deleted after TTL
- Job status visible in real-time
- Tests passing in CI

---

## 4. Phase 2 — Core Tools (Weeks 5–7)

**Goal:** Add Split, Compress, Rotate tools. Prove the tool registry pattern works for rapid tool addition.

### Milestone 2: "4 Working Tools"

| Task | Effort |
|------|--------|
| Split PDF handler + config schema + page | 16h |
| Compress PDF handler (pikepdf) + config schema + page | 16h |
| Rotate PDF handler + config schema + page | 12h |
| PDF thumbnail/preview generation | 8h |
| Tool page template (shared layout) | 6h |
| All Tools directory page | 4h |
| Unit + integration tests for each tool | 12h |
| **Total** | **~74h** |

**Exit criteria:** 4 tools working end-to-end, each using the shared pipeline.

---

## 5. Phase 3 — Polish & Launch (Weeks 8–10)

**Goal:** Production-ready quality, SEO, public launch.

### Milestone 3: "Public Launch"

| Task | Effort |
|------|--------|
| SEO: meta tags, structured data, sitemap | 6h |
| SEO: per-tool landing page copy (FAQ, how-to) | 8h |
| Responsive design polish (mobile, tablet) | 8h |
| Error states and empty states | 4h |
| Loading skeletons and animations | 4h |
| Privacy policy and terms pages | 4h |
| 404 and error pages | 2h |
| Sentry error tracking setup | 2h |
| Production deployment setup (Railway/Render) | 8h |
| Cloudflare R2 setup | 4h |
| Cloudflare DNS + CDN setup | 2h |
| Google Search Console + Analytics | 2h |
| E2E tests (Playwright) | 8h |
| Performance audit (Lighthouse) | 4h |
| Security audit (headers, CORS, rate limits) | 4h |
| Staging environment + smoke tests | 4h |
| **Total** | **~74h** |

**Exit criteria:** Live on production URL, indexed by Google, all Lighthouse scores > 90.

---

## 6. Phase 4 — Users & Monetization (Weeks 11–16)

### Milestone 4: "User Accounts + Pro Tier"

| Feature | Effort |
|---------|--------|
| User registration/login (email + password) | 16h |
| OAuth (Google, GitHub) | 12h |
| JWT authentication + refresh tokens | 8h |
| User dashboard (job history) | 12h |
| Stripe integration (checkout, portal, webhooks) | 20h |
| Pro tier limits enforcement | 8h |
| Pricing page | 6h |
| Additional tools: Extract, Delete, Reorder pages | 24h |
| Additional tools: Watermark, Page numbers | 16h |
| Additional tools: Protect/Unlock PDF | 12h |

---

## 7. Phase 5 — Conversion Tools (Weeks 17–22)

### Milestone 5: "Conversion Suite"

| Feature | Effort |
|---------|--------|
| Image → PDF (Pillow) | 12h |
| PDF → Image (pdf2image + poppler) | 16h |
| PDF → Word (LibreOffice CLI) | 16h |
| PDF → Excel (LibreOffice CLI) | 8h |
| PDF → PowerPoint (LibreOffice CLI) | 8h |
| OCR (Tesseract) | 16h |
| Batch operations | 12h |

---

## 8. Phase 6 — Advanced Tools (Weeks 23–30)

| Feature |
|---------|
| Edit PDF (annotations, text) |
| Compare PDF (visual diff) |
| Redact PDF |
| PDF Forms (fill & flatten) |
| Public API + API keys |
| Webhooks |
| API documentation page |

---

## 9. Phase 7 — AI & Enterprise (Weeks 31+)

| Feature |
|---------|
| AI Summarization (LLM integration) |
| Ask PDF (RAG-based chat) |
| PDF Translation |
| Structured data extraction |
| Workflows (tool chaining) |
| Team/Business accounts |
| SSO/SAML |

---

## 10. Risk-Adjusted Timeline

| Phase | Optimistic | Realistic | Pessimistic |
|-------|-----------|-----------|-------------|
| Phase 0: Setup | 1 week | 1 week | 2 weeks |
| Phase 1: Foundation | 2 weeks | 3 weeks | 5 weeks |
| Phase 2: Core Tools | 2 weeks | 3 weeks | 4 weeks |
| Phase 3: Launch | 2 weeks | 3 weeks | 4 weeks |
| **MVP Total** | **7 weeks** | **10 weeks** | **15 weeks** |
