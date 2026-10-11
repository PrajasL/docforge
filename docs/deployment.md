# Deployment Strategy

## 1. Overview

DocForge uses a **containerized deployment** approach. All services (API, workers, frontend) run in Docker containers, orchestrated with Docker Compose locally and a managed container platform in production.

---

## 2. Environments

| Environment | Purpose | Infrastructure | URL |
|-------------|---------|---------------|-----|
| **Local** | Development | Docker Compose on developer machine | `localhost:3000` (frontend), `localhost:8000` (API) |
| **CI** | Automated testing | GitHub Actions with Docker Compose | — |
| **Staging** | Pre-production testing | Same as production, smaller resources | `staging.docforge.com` |
| **Production** | Live users | Managed container platform | `docforge.com` |

---

## 3. Local Development Stack

```yaml
# docker-compose.yml (conceptual structure)
services:
  # --- Infrastructure ---
  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes: [minio_data:/data]

  # --- Application ---
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis, minio]
    volumes: [./backend:/app]  # Hot reload

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info
    depends_on: [postgres, redis, minio]
    volumes: [./backend:/app]

  beat:
    build: ./backend
    command: celery -A app.workers.celery_app beat --loglevel=info
    depends_on: [redis]

  flower:
    image: mher/flower
    ports: ["5555:5555"]
    depends_on: [redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    volumes: [./frontend:/app, /app/node_modules]
    depends_on: [api]
```

### Developer Workflow
```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f api worker

# Run backend tests
docker compose exec api pytest

# Run migrations
docker compose exec api alembic upgrade head

# Stop everything
docker compose down
```

---

## 4. Production Deployment Strategy

### Phase 1: MVP (Simple Platform)

**Recommended platform:** **Railway** or **Render**

**Why:**
- Zero DevOps overhead — managed containers, auto-deploy from Git
- Built-in PostgreSQL and Redis addons
- Automatic HTTPS
- Affordable for low traffic ($5–20/month)
- Easy to migrate away from later

**Services to deploy:**
| Service | Platform Feature | Scaling |
|---------|-----------------|---------|
| Frontend (Next.js) | Web Service or Vercel | Auto |
| API (FastAPI) | Web Service | Manual (1–2 instances) |
| Worker (Celery) | Background Worker | Manual (1–2 instances) |
| Beat (Celery Beat) | Background Worker | 1 instance only |
| PostgreSQL | Managed addon | Platform-managed |
| Redis | Managed addon | Platform-managed |
| Object Storage | Cloudflare R2 | Pay-per-use |

### Phase 2: Growth (Container Orchestration)

**Recommended platform:** **AWS ECS Fargate** or **GCP Cloud Run**

**When to migrate:**
- Traffic exceeds platform limits
- Need auto-scaling workers
- Need multi-region deployment
- Cost optimization at scale

### Phase 3: Scale

- Kubernetes (EKS/GKE) if team and traffic justify the operational overhead
- This is a distant concern — do not plan for Kubernetes in MVP

---

## 5. CI/CD Pipeline

```
┌──────────┐    ┌───────────┐    ┌────────────┐    ┌─────────────┐
│  Push /  │───►│   Lint    │───►│   Tests    │───►│   Build     │
│  PR      │    │           │    │            │    │             │
│          │    │ ruff      │    │ Unit       │    │ Docker      │
│          │    │ mypy      │    │ Integration│    │ images      │
│          │    │ eslint    │    │            │    │             │
└──────────┘    └───────────┘    └────────────┘    └──────┬──────┘
                                                          │
                                              ┌───────────┴───────────┐
                                              │                       │
                                         PR merge              Push to main
                                              │                       │
                                              ▼                       ▼
                                        ┌──────────┐          ┌──────────────┐
                                        │ No deploy│          │ Deploy to    │
                                        │          │          │ Staging      │
                                        └──────────┘          └──────┬───────┘
                                                                     │
                                                              Manual approval
                                                                     │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │ Deploy to    │
                                                              │ Production   │
                                                              └──────────────┘
```

### CI Tool: **GitHub Actions**
- **Why:** Free for public repos, generous free tier for private, excellent Docker support, marketplace for actions

### Deployment Steps
1. Build Docker images for API + Worker
2. Push to container registry (GitHub Container Registry or Docker Hub)
3. Deploy to staging automatically on `main` merge
4. Manual promotion to production after staging verification
5. Run smoke tests after production deploy
6. Automatic rollback if health check fails

---

## 6. Docker Image Strategy

### Multi-Stage Builds
```dockerfile
# Conceptual Dockerfile structure for backend
# Stage 1: Dependencies
FROM python:3.12-slim AS deps
# Install system deps (poppler, etc.) and Python packages

# Stage 2: Application
FROM deps AS app
COPY . /app
# Non-root user, health check, entrypoint
```

### Image Optimization
- Use `python:3.12-slim` (not `python:3.12` — saves ~600 MB)
- Use `node:20-alpine` for frontend build
- Multi-stage builds to exclude build tools from final image
- `.dockerignore` to exclude tests, docs, `.git`
- Pin base image digests for reproducibility in production

---

## 7. Configuration Management

### Environment Variables

| Variable | Dev Default | Production |
|----------|------------|------------|
| `DATABASE_URL` | `postgresql://...localhost:5432/docforge` | Platform-provided |
| `REDIS_URL` | `redis://localhost:6379/0` | Platform-provided |
| `STORAGE_ENDPOINT` | `http://localhost:9000` | R2/S3 endpoint |
| `STORAGE_BUCKET` | `docforge-dev` | `docforge-prod` |
| `STORAGE_ACCESS_KEY` | MinIO default | R2/S3 credentials |
| `STORAGE_SECRET_KEY` | MinIO default | R2/S3 credentials |
| `CORS_ORIGINS` | `http://localhost:3000` | `https://docforge.com` |
| `SECRET_KEY` | `dev-secret-change-me` | Random 64-char string |
| `ENVIRONMENT` | `development` | `production` |
| `LOG_LEVEL` | `DEBUG` | `INFO` |
| `FILE_TTL_HOURS` | `2` | `2` |
| `MAX_FILE_SIZE_MB` | `50` | `50` |

### Configuration Hierarchy
1. Environment variables (highest priority)
2. `.env` file (local development only)
3. Default values in code (lowest priority)

---

## 8. Monitoring & Observability

### MVP Monitoring
| What | Tool | Why |
|------|------|-----|
| Application logs | Platform built-in (Railway/Render) | Zero setup |
| Error tracking | **Sentry** (free tier) | Exception tracking with context |
| Uptime monitoring | **UptimeRobot** (free tier) | Alerts when service is down |
| Task monitoring | **Flower** (self-hosted) | Celery task dashboard |

### Growth Monitoring
| What | Tool |
|------|------|
| APM | Sentry Performance or Datadog |
| Metrics | Prometheus + Grafana |
| Log aggregation | Loki or CloudWatch |
| Alerting | PagerDuty or OpsGenie |

### Key Metrics to Track
- API response time (P50, P95, P99)
- Job processing time per tool
- Job success/failure rate
- Worker queue depth
- Storage usage
- Active concurrent users
- Error rate by endpoint

---

## 9. Backup Strategy

| Data | Backup Method | Frequency | Retention |
|------|--------------|-----------|-----------|
| PostgreSQL | Platform automated backups | Daily | 30 days |
| Redis | Not backed up (ephemeral cache/queue) | — | — |
| Object Storage | R2/S3 versioning (optional) | Continuous | 7 days |
| Source code | Git (GitHub) | Every push | Permanent |
| Secrets | Documented in secure vault | On change | Permanent |

---

## 10. Rollback Strategy

1. **Instant rollback:** Re-deploy previous Docker image tag
2. **Database rollback:** Alembic downgrade (all migrations must be reversible)
3. **Feature flags:** Use environment variables to disable problematic features without redeploying
4. **Blue-green deploys:** Production platform should support zero-downtime deploys (Railway/Render do this automatically)
