import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

# Import database module and models so SQLAlchemy metadata is registered
# for Alembic migrations. Health endpoints continue to use psycopg directly.
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
        with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return {"database": "ok"}
    except Exception as e:
        print("DB ERROR:", repr(e))
        raise HTTPException(status_code=503, detail="Database not reachable")