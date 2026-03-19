import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

db_url = settings.DATABASE_URL

# ── Decide driver ───────────────────────────────────────────────────────────
# If psycopg2 is not installed, fall back to local SQLite for development
_use_sqlite = False

if "postgresql" in db_url or "postgres" in db_url:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print("psycopg2 not installed – falling back to local SQLite database")
        _use_sqlite = True

if _use_sqlite or db_url.startswith("sqlite"):
    db_path = os.path.join(os.path.dirname(__file__), "..", "tourist_safety.db")
    db_url = f"sqlite:///{os.path.abspath(db_path)}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
else:
    # Normalize driver prefix for PostgreSQL
    for prefix in ("ppostgresql://", "postgresql+psycopg2://", "postgresql://", "postgres://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+psycopg2://" + db_url[len(prefix):]
            break

    # Strip ?sslmode=... from URL (we handle SSL via connect_args)
    if "?" in db_url:
        db_url = db_url.split("?")[0]

    connect_args = {
        "sslmode": "require",
        "connect_timeout": 10,
    }

    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
