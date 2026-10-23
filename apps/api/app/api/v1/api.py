"""API v1 router aggregator.

Includes all version-1 route modules under the /api/v1 prefix.
Public read endpoints are accessible without authentication.
Write endpoints require development-mode authorization (see app/auth.py).
"""

from fastapi import APIRouter

from app.api.v1.routers import hospitals, doctors, labs, tests, directory

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(hospitals.router)
api_router.include_router(doctors.router)
api_router.include_router(labs.router)
api_router.include_router(tests.router)
api_router.include_router(directory.router)
