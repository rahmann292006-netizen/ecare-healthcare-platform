import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

load_dotenv()

# Import database module and models so SQLAlchemy metadata is registered
# for Alembic migrations and use its configured engine for health checks.
from app.database import engine, Base  # noqa: E402
import app.models  # noqa: E402, F401  (registers all models with Base.metadata)

from app.api.v1.api import api_router  # noqa: E402

app = FastAPI(title="ecare API")

# CORS configuration from environment. Defaults to the local Next.js
# frontend origin. Never allows all origins in production-like settings.
_cors_origins_env = os.environ.get("ECARE_CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception as exc:
        print(f"DB connectivity check failed ({type(exc).__name__})")
        raise HTTPException(status_code=503, detail="Database not reachable")
