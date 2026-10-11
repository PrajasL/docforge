# Security Architecture

## 1. Threat Model

DocForge processes user-uploaded PDF files — a format historically associated with malware delivery, code execution exploits, and data exfiltration. Security must be a first-class concern from day one.

### Attack Surfaces

| Surface | Threats | Severity |
|---------|---------|----------|
| **File Upload** | Malicious PDFs, oversized files, path traversal | Critical |
| **PDF Processing** | Code execution via crafted PDFs, DoS via resource exhaustion | Critical |
| **API** | Injection, authentication bypass, rate limit circumvention | High |
| **Object Storage** | Unauthorized access, URL enumeration | High |
| **User Data** | Data leakage, GDPR violations | High |
| **Infrastructure** | Container escape, secrets exposure | High |
| **Frontend** | XSS, CSRF, clickjacking | Medium |

---

## 2. File Upload Security

### Validation Chain
```
Client-side check (UX only, not trusted)
    ↓
API server validation (size, count, MIME type)
    ↓
Worker deep validation (magic bytes, PDF structure, malicious patterns)
    ↓
Processing in isolated temp directory
```

### Upload Protections
- **File size limits** enforced at multiple layers (nginx, API, storage policy)
- **Content-Type whitelist** per tool (e.g., merge only accepts `application/pdf`)
- **No filename trust** — files are renamed to `{file_id}.{ext}` immediately; original name stored in DB only
- **No path from user input** — storage keys are constructed server-side from UUIDs
- **Upload timeout** — presigned URLs expire after 15 minutes
- **Checksum verification** — SHA-256 computed on upload, verified before processing

### Malicious PDF Detection
```
Scan for:
├── /JS, /JavaScript        (embedded scripts)
├── /OpenAction, /AA         (automatic actions)
├── /Launch                  (launch external applications)
├── /SubmitForm              (data exfiltration)
├── /ImportData              (import external data)
├── /EmbeddedFile            (embedded executables)
├── /URI with suspicious domains
└── Excessive nesting / recursion (zip-bomb equivalent)
```

**MVP approach:** Log and flag suspicious elements. Do not block processing (many legitimate PDFs trigger these). Provide metrics for later analysis.

**Future:** Configurable security levels (allow-all, warn, block-suspicious).

---

## 3. Processing Isolation

### Worker Container Hardening
- Workers run as **non-root** user inside Docker containers
- Each job gets its own temporary directory (`/tmp/docforge/jobs/{job_id}/`)
- **No network access** from worker containers to external internet (only to storage and database)
- **Resource limits** per container:
  - Memory: 1 GB (hard limit)
  - CPU: 1 core per worker
  - Disk: 2 GB temp space per worker
  - Process limit: 64 (prevent fork bombs)
- **Celery task timeouts:**
  - Soft timeout: 240 seconds (allows cleanup)
  - Hard timeout: 300 seconds (SIGKILL)
- Temp directories cleaned after every job (success or failure)
- Workers should NOT have database write access to tables other than `jobs` and `files`

### Future Enhancements
- Run each job in a disposable container (gVisor or Firecracker)
- AppArmor/SELinux profiles for worker processes
- Separate worker pools for trusted (authenticated user) vs untrusted (anonymous) files

---

## 4. API Security

### Input Validation
- All input validated with **Pydantic v2** schemas (strict mode)
- SQL injection prevented by **SQLAlchemy** parameterized queries
- No raw SQL in application code
- Request body size limited to 10 MB (file data goes to storage, not API)

### Rate Limiting
- Implemented via **Redis** sliding window counters
- Applied per IP address (anonymous) and per user ID (authenticated)
- Different limits per tier (see API Spec)
- Returned in response headers (`X-RateLimit-*`)
- Rate limit bypass attempts logged and monitored

### CORS
- Strict origin allowlist: `https://docforge.com`, `http://localhost:3000` (dev)
- No wildcard origins in production
- `Access-Control-Allow-Credentials: true` only for authenticated endpoints

### Headers
All responses include:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 0  (rely on CSP instead)
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

## 5. Object Storage Security

### Access Control
- **Presigned URLs** for all uploads and downloads — bucket is NEVER public
- Upload presigned URLs: 15-minute expiry, scoped to specific key + content type
- Download presigned URLs: 5-minute expiry
- Storage bucket policy: deny all public access

### Key Design
- Storage keys use UUIDs, not user-provided filenames
- Keys are date-partitioned: `inputs/{YYYY}/{MM}/{DD}/{job_id}/{file_id}.pdf`
- No directory listing enabled on bucket
- CORS configured to allow PUT only from known origins

### Encryption
- **At rest:** S3/R2 server-side encryption (AES-256 / SSE-S3)
- **In transit:** TLS 1.2+ for all storage operations
- **MinIO (dev):** Encryption disabled for simplicity; enable in staging/prod

---

## 6. Authentication Security (Tier 2)

### Password Handling
- Hashed with **bcrypt** (cost factor 12)
- Minimum 8 characters, maximum 128 characters
- No password in logs, error messages, or API responses
- Rate-limited login attempts (5 failures per 15 minutes per email)
- Account lockout after 10 consecutive failures (30-minute cooldown)

### JWT Tokens
- **Access token:** 15-minute expiry, stored in memory (not localStorage)
- **Refresh token:** 7-day expiry, stored in HttpOnly Secure SameSite=Strict cookie
- Tokens signed with RS256 (asymmetric — API only needs public key to verify)
- Token revocation via Redis blocklist (for logout/password change)

### OAuth
- Supported providers: Google, GitHub (Tier 2)
- State parameter for CSRF protection
- PKCE flow for additional security
- Link OAuth identities to existing accounts by email

---

## 7. Data Privacy

### File Privacy
- **No file content logging** — only metadata (size, type, page count)
- **No file content analytics** — files are never read for marketing/ML purposes
- **Automatic deletion** — files deleted after TTL (2h free, 24h pro)
- **User-initiated deletion** — users can delete jobs/files immediately
- **Processing isolation** — one job cannot access another job's files

### GDPR Compliance
- Data export: users can export their job history (JSON)
- Data deletion: users can request full account deletion
- Right to be forgotten: complete data purge within 30 days
- Data processing agreement (DPA) available for business customers
- Cookie consent banner (only if using analytics cookies)
- Privacy policy accessible from every page

### Logging
- **Do log:** Request metadata (IP, user agent, endpoint, status code, duration)
- **Do log:** Job events (created, started, completed, failed)
- **Do NOT log:** File contents, user passwords, full API keys
- **IP addresses:** Anonymized after 30 days (truncate last octet)
- **Log retention:** 90 days, then purged

---

## 8. Infrastructure Security

### Secrets Management
- **Development:** `.env` files (never committed, in `.gitignore`)
- **Production:** Environment variables injected by platform (Railway/Render) or secrets manager
- **Never hardcode** secrets in source code
- **Rotate** database passwords and API keys quarterly

### Dependencies
- **Dependabot / Renovate** for automatic dependency updates
- **pip-audit** in CI to check for known vulnerabilities
- **npm audit** in CI for frontend dependencies
- Pin major versions, allow patch updates
- Review changelogs before major upgrades

### Container Security
- Base images: `python:3.12-slim` (minimal surface)
- No SSH access to containers
- Read-only root filesystem where possible
- Non-root user for all application processes
- Health checks for auto-restart on failure

---

## 9. Monitoring & Incident Response

### Security Monitoring
- Failed authentication attempts → alert after threshold
- Unusual upload patterns (size, frequency) → alert
- Worker crashes / OOM → alert
- Rate limit violations → metrics dashboard
- Error rate spikes → alert

### Incident Response Plan
1. **Detect** — Automated alerts via monitoring
2. **Contain** — Disable affected tool / rate limit source IP
3. **Investigate** — Review logs (no file content in logs)
4. **Remediate** — Patch vulnerability, rotate compromised credentials
5. **Communicate** — Notify affected users if data was exposed
6. **Post-mortem** — Document and improve

---

## 10. Security Checklist for MVP

- [ ] All storage buckets are private (no public access)
- [ ] Presigned URLs have short expiry times
- [ ] File uploads validate type, size, and structure
- [ ] Worker containers run as non-root
- [ ] Worker containers have resource limits
- [ ] No raw SQL in application code
- [ ] Rate limiting is active on all endpoints
- [ ] CORS is configured with explicit origin allowlist
- [ ] Security headers are set on all responses
- [ ] Secrets are not in source code
- [ ] Dependencies are scanned for vulnerabilities
- [ ] Temporary files are cleaned up after processing
- [ ] UUIDs used for all IDs (no enumeration)
- [ ] No file content in logs
- [ ] HTTPS enforced in production
