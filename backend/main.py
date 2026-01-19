from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import get_settings
from database import connect_to_mongo, close_mongo_connection
from middleware import SessionMiddleware
from routers import projects_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="MCHacks 2026 API",
    description="Backend API for video editing application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for anonymous user tracking
app.add_middleware(SessionMiddleware)

# Include routers
app.include_router(projects_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "MCHacks 2026 API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
