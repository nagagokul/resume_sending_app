from fastapi import APIRouter

from app.api import applications, auth, dashboard, jobs, resume

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(resume.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(dashboard.router)
