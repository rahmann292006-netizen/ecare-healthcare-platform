from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from sqlalchemy import text

load_dotenv()

# Import database module and models so SQLAlchemy metadata is registered
# for Alembic migrations and use its configured engine for health checks.
from app.database import engine, Base  # noqa: E402
import app.models  # noqa: E402, F401  (registers all models with Base.metadata)

from app.api.v1.api import api_router  # noqa: E402

app = FastAPI(title="ecare API")

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
