from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Normalize DB URL: strip any sslmode param so we can pass it via connect_args instead
db_url = settings.DATABASE_URL

# Normalize driver prefix
for prefix in ("ppostgresql://", "postgresql+psycopg2://", "postgresql://", "postgres://"):
    if db_url.startswith(prefix):
        db_url = "postgresql+psycopg2://" + db_url[len(prefix):]
        break

# Strip ?sslmode=... from URL (we handle SSL via connect_args below)
if "?" in db_url:
    db_url = db_url.split("?")[0]

# psycopg2 connect_args for Render-hosted PostgreSQL
# Render requires SSL but the connection is abruptly closed if sslmode is in the URL
connect_args = {
    "sslmode": "require",
    "connect_timeout": 10,
}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,      # test connections before using them from the pool
    pool_recycle=300,         # recycle connections every 5 min (Render drops idle after ~5min)
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

