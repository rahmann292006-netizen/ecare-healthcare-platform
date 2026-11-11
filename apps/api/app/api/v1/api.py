"""API v1 router aggregator.

Includes all version-1 route modules under the /api/v1 prefix.
Public read endpoints are accessible without authentication.
Write endpoints allow a development-only shortcut or require an active admin.
"""

from fastapi import APIRouter

from app.api.v1.routers import (
    hospitals,
    doctors,
    labs,
    tests,
    directory,
    auth,
    appointments,
    family_members,
    reminders,
    packages,
    subscriptions,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(hospitals.router)
api_router.include_router(doctors.router)
api_router.include_router(labs.router)
api_router.include_router(tests.router)
api_router.include_router(directory.router)
api_router.include_router(auth.router)
api_router.include_router(appointments.router)
api_router.include_router(family_members.router)
api_router.include_router(reminders.router)
api_router.include_router(packages.router)
api_router.include_router(subscriptions.router)
