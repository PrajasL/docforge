# Development Rules

## 1. Code Organization

### General
- **No premature abstraction** — Write concrete code first, abstract when you see the pattern repeated 3 times
- **No dead code** — Delete unused code, don't comment it out
- **No TODO without a ticket** — Every `TODO` must reference a backlog item
- **One concern per file** — Keep files focused; split when a file exceeds ~300 lines
- **Explicit over implicit** — Prefer verbose, clear code over clever, compact code

### Backend (Python / FastAPI)
- **Type hints everywhere** — All function signatures must have type annotations
- **Pydantic for all I/O** — Request/response schemas are always Pydantic models
- **No raw SQL** — Use SQLAlchemy ORM or core expressions only
- **No business logic in routes** — Routes call service functions; services contain logic
- **No ORM objects in Celery tasks** — Pass IDs, re-fetch in the worker
- **Async by default** — Use `async def` for all API endpoints
- **Config via environment** — No hardcoded config values; use `Settings` class

### Frontend (Next.js / TypeScript)
- **Strict TypeScript** — `strict: true` in tsconfig, no `any` types
- **Server Components by default** — Use client components (`'use client'`) only when needed for interactivity
- **No inline styles** — Use Tailwind classes or CSS modules
- **Accessible** — All interactive elements must be keyboard-navigable and have ARIA labels
- **No prop drilling beyond 2 levels** — Use context or Zustand for shared state

### Workers (Celery)
- **Idempotent tasks** — Every task can be safely retried
- **No file content in task arguments** — Pass storage keys, download in worker
- **Always clean up** — `try/finally` to delete temp files, even on exceptions
- **Report progress** — All long-running tasks must emit progress events
- **Respect cancellation** — Check cancellation token periodically during processing

---

## 2. Git Workflow

### Branch Strategy
```
main              — Production-ready code, auto-deploys to staging
├── feature/*     — New features (branch from main)
├── fix/*         — Bug fixes (branch from main)
├── chore/*       — Maintenance tasks (branch from main)
└── release/*     — Release preparation (branch from main)
```

### Commit Messages
Follow **Conventional Commits**:
```
feat: add split PDF handler
fix: correct page count in merge result
chore: update pypdf to 4.1.0
docs: add API rate limiting documentation
test: add integration tests for compress pipeline
refactor: extract storage abstraction interface
```

### Pull Request Rules
- PRs must have a description explaining **why**, not just what
- All CI checks must pass
- At least 1 approval required (when team > 1)
- Squash merge to main (clean history)
- Branch deleted after merge
- No direct pushes to `main`

---

## 3. API Design Rules

- **Always version** — `/api/v1/` prefix on all endpoints
- **Standard envelope** — All responses use `{ success, data, error, meta }`
- **Meaningful HTTP status codes** — Don't return 200 for errors
- **Machine-readable error codes** — e.g., `FILE_TOO_LARGE`, not just "Bad Request"
- **Plural resource names** — `/jobs`, `/files`, `/tools`
- **UUIDs for IDs** — Never sequential integers in URLs
- **Pagination** — Cursor-based, never offset-based (for consistency at scale)
- **Rate limit headers** — Include `X-RateLimit-*` on all responses
- **No breaking changes** — Add new fields freely; never remove or rename existing fields in same version

---

## 4. Database Rules

- **Migrations are mandatory** — Never modify schema manually; always use Alembic
- **Migrations are reversible** — Every `upgrade()` must have a matching `downgrade()`
- **No nullable columns without a reason** — Default to `NOT NULL`
- **UUID primary keys** — All tables use UUIDv4
- **Timestamps in UTC** — All `TIMESTAMPTZ` columns store UTC
- **Index for every frequent query** — No unindexed foreign keys
- **No cascade deletes** — Explicit deletion logic in application code

---

## 5. Security Rules

- **Never trust client input** — Validate on server AND worker
- **No secrets in code** — Environment variables or secrets manager only
- **No file paths from user input** — Construct all paths server-side
- **No raw file names** — Rename to `{uuid}.{ext}` immediately
- **Log metadata, never content** — File sizes yes, file contents never
- **Presigned URLs for all file access** — Bucket is never public
- **Rate limit all endpoints** — Including unauthenticated ones

---

## 6. Testing Rules

- **No PR without tests** — New features require tests; bug fixes require regression tests
- **Test behavior, not implementation** — Tests should survive refactoring
- **Test edge cases for PDFs** — Empty, corrupted, huge, encrypted, mixed page sizes
- **Integration tests use real containers** — Don't mock the database or storage in integration tests
- **Unit tests mock external dependencies** — Mock S3, mock Redis in unit tests
- **Coverage must not decrease** — CI enforces coverage threshold

---

## 7. Documentation Rules

- **Update docs with code changes** — If you change an API, update the API spec
- **README is always current** — Local dev setup must work by following README
- **Code comments explain WHY** — The code explains what; comments explain why
- **No outdated comments** — If you change code, update nearby comments
- **ADRs for major decisions** — Document architectural decisions in `docs/decisions/`

---

## 8. Performance Rules

- **No N+1 queries** — Use eager loading or batch queries
- **No blocking calls in async routes** — Use `run_in_threadpool` for sync operations
- **Stream large responses** — Don't load entire files into memory
- **Clean up temp files** — Never leave files on disk after job completion
- **Measure before optimizing** — Profile first, optimize second

---

## 9. Dependency Rules

- **Review licenses before adding** — No AGPL or GPL dependencies embedded in the application
- **Pin major versions** — `pypdf>=4.0,<5.0` not `pypdf`
- **Minimize dependencies** — If the stdlib can do it, don't add a package
- **Update regularly** — Monthly dependency updates; address security advisories immediately
- **No vendor lock-in** — Abstract external services behind interfaces (storage, email, payments)

---

## 10. Definition of Done

A feature is "done" when:
- [ ] Code is written and follows all rules above
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] API documentation updated (if applicable)
- [ ] No new lint warnings
- [ ] No new security vulnerabilities
- [ ] PR reviewed and approved
- [ ] Merged to main
- [ ] Verified on staging
