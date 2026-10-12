from fastapi import APIRouter

from app.api.v1.endpoints import health, jobs

api_router = APIRouter()

# Health endpoints
api_router.include_router(health.router)

# Jobs endpoints
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
