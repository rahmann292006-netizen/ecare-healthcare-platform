"""Database configuration and session management for eCare API.

Reads DATABASE_URL from environment variables (loaded via python-dotenv).
Never hardcodes database credentials.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Yield a transactional SQLAlchemy session and close it after use.

    Commits on successful completion, rolls back on exception.
    Intended for use as a FastAPI dependency.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()