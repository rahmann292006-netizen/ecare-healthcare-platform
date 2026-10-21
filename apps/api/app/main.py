import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()

app = FastAPI(title="ecare API")


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