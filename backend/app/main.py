from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routes import auth, tourist, police, websocket

logger = logging.getLogger("tourist_safety")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f" Database connection failed on startup: {e}")
        logger.error("Auth/DB endpoints will return 500 until DB is reachable.")
    yield
    # Shutdown: nothing to clean up


app = FastAPI(
    title="Smart Tourist Safety Monitoring System",
    description="AI-powered real-time tourist safety monitoring with 4 ML models",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tourist.router)
app.include_router(police.router)
app.include_router(websocket.router)


@app.get("/")
def root():
    return {
        "message": "Smart Tourist Safety Monitoring & Incident Response System",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
