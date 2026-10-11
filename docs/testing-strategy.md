# Testing Strategy

## 1. Overview

DocForge uses a **testing pyramid** approach: many fast unit tests, focused integration tests, and a small number of end-to-end tests. The goal is high confidence in the PDF processing pipeline while keeping test execution fast enough for CI.

---

## 2. Testing Pyramid

```
           ┌─────────┐
           │  E2E    │  ~5-10 tests
           │ (slow)  │  Full browser tests
          ┌┴─────────┴┐
          │Integration │  ~30-50 tests
          │  (medium)  │  API + Worker + Storage
         ┌┴────────────┴┐
         │   Unit Tests  │  ~200+ tests
         │   (fast)      │  Pure logic, handlers, validators
         └───────────────┘
```

---

## 3. Test Categories

### 3.1 Unit Tests

**Backend (pytest)**

| Module | What to Test | Example |
|--------|-------------|---------|
| Tool handlers | PDF processing logic | Merge 2 PDFs produces correct page count |
| Validators | File validation | Reject non-PDF file with PDF extension |
| Job state machine | State transitions | PENDING → QUEUED is valid, COMPLETED → PENDING is invalid |
| Config schemas | Tool config validation | Missing `file_order` in merge config is rejected |
| Storage abstraction | Key generation | Storage key follows expected format |
| Rate limiter | Limit enforcement | 11th request in window returns 429 |

**Frontend (Vitest + React Testing Library)**

| Component | What to Test | Example |
|-----------|-------------|---------|
| FileDropzone | File validation | Rejects non-PDF files with error message |
| JobTracker | State rendering | Shows progress bar when PROCESSING |
| ToolPage | Config form | Merge page shows file reorder controls |
| API client | Error handling | Displays rate limit message on 429 |

### 3.2 Integration Tests

Run against real Docker containers (PostgreSQL, Redis, MinIO) using Docker Compose.

| Test Scenario | Components | Expected Outcome |
|--------------|------------|------------------|
| Create job + upload + start | API + DB + Storage | Job transitions to QUEUED |
| Full merge pipeline | API + Worker + DB + Storage | Job COMPLETED, result downloadable |
| Full split pipeline | API + Worker + DB + Storage | Job COMPLETED, ZIP result |
| File cleanup | Worker + DB + Storage | Expired files deleted from storage |
| Rate limiting | API + Redis | Requests blocked after limit |
| Presigned URL expiry | API + Storage | Expired URL returns 403 |
| Concurrent job limit | API + Redis | Job creation blocked at limit |

### 3.3 End-to-End Tests

Browser-based tests using **Playwright**.

| Test Scenario | Steps |
|--------------|-------|
| Merge 2 PDFs | Navigate → Drop files → Reorder → Merge → Download |
| Split PDF | Navigate → Drop file → Set ranges → Split → Download |
| Error handling | Upload invalid file → Verify error message |
| Large file | Upload 40 MB PDF → Verify progress → Download |

### 3.4 PDF-Specific Tests

A dedicated test suite for edge cases in PDF processing:

| Test Case | Input | Expected |
|-----------|-------|----------|
| Empty PDF (0 pages) | empty.pdf | Error: "PDF has no pages" |
| Single page PDF | 1-page.pdf | Processed successfully |
| Large PDF (500 pages) | large.pdf | Processed within timeout |
| Password-protected PDF | encrypted.pdf | Error: "PDF is password-protected" |
| Corrupted PDF | corrupted.pdf | Error: "Invalid PDF structure" |
| PDF with forms | forms.pdf | Processed (forms preserved) |
| PDF with images | image-heavy.pdf | Processed successfully |
| PDF with embedded fonts | fonts.pdf | Processed (fonts preserved) |
| Mixed page sizes | mixed-sizes.pdf | Processed (sizes preserved) |
| PDF/A compliant | pdfa.pdf | Processed successfully |

> **Test fixtures:** Create a `tests/fixtures/` directory with sample PDFs for each edge case. These should be small (< 100 KB each) and committed to the repo.

---

## 4. Test Infrastructure

### Backend Test Stack
```
pytest              — Test runner
pytest-asyncio      — Async test support (FastAPI)
pytest-cov          — Code coverage
httpx               — Async HTTP client for API tests
factory-boy         — Test data factories
testcontainers      — Docker containers for integration tests
fakeredis           — In-memory Redis for unit tests
moto                — Mock AWS S3 for unit tests
```

### Frontend Test Stack
```
vitest              — Test runner (Vite-native)
@testing-library/react — Component testing
msw                 — API mocking (Mock Service Worker)
playwright          — E2E browser tests
```

### Docker Compose for Testing
```yaml
# docker-compose.test.yml (conceptual)
services:
  postgres-test:
    image: postgres:16
    environment:
      POSTGRES_DB: docforge_test
    tmpfs: /var/lib/postgresql/data  # RAM disk for speed

  redis-test:
    image: redis:7

  minio-test:
    image: minio/minio
    command: server /data
```

---

## 5. Coverage Targets

| Component | Minimum Coverage | Target Coverage |
|-----------|-----------------|----------------|
| Tool handlers | 90% | 95% |
| API endpoints | 80% | 90% |
| Job state machine | 95% | 100% |
| Validators | 90% | 95% |
| Storage abstraction | 80% | 90% |
| Frontend components | 70% | 80% |
| Frontend hooks/utils | 80% | 90% |
| Overall backend | 80% | 85% |
| Overall frontend | 70% | 80% |

---

## 6. CI Pipeline

```
┌─────────┐    ┌─────────────┐    ┌──────────────┐    ┌────────────┐
│  Lint   │───►│ Unit Tests  │───►│ Integration  │───►│  E2E Tests │
│         │    │             │    │ Tests        │    │            │
│ ruff    │    │ pytest      │    │ pytest +     │    │ Playwright │
│ mypy    │    │ vitest      │    │ docker       │    │            │
│ eslint  │    │             │    │ compose      │    │            │
│ prettier│    │ ~30 seconds │    │ ~3 minutes   │    │ ~5 minutes │
└─────────┘    └─────────────┘    └──────────────┘    └────────────┘
     │                │                  │                   │
     └────────────────┴──────────────────┴───────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │  Coverage Report      │
                    │  Security Scan        │
                    │  (pip-audit, npm audit)│
                    └───────────────────────┘
```

### CI Rules
- All PRs must pass lint + unit tests before merge
- Integration tests run on every PR
- E2E tests run on merge to `main`
- Coverage must not decrease on PRs
- Security scan blocks merge on critical vulnerabilities
- Test runs are parallelized where possible

---

## 7. Local Development Testing

```bash
# Run backend unit tests (fast, no Docker needed)
pytest tests/unit/ -v

# Run backend integration tests (needs Docker)
docker compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v

# Run frontend unit tests
npm run test

# Run E2E tests (needs full stack running)
npm run test:e2e
```

---

## 8. Test Data Management

- **Factories:** Use `factory-boy` to create test data (jobs, files, users)
- **Fixtures:** PDF test files in `tests/fixtures/pdfs/`
- **Seeding:** Development seed script creates sample jobs in all states
- **Cleanup:** Each integration test cleans up after itself (database transaction rollback)
- **Deterministic:** Tests do not depend on external services or time (mock `datetime.now()`)
