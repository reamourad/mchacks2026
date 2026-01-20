import os
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from database import connect_to_mongo, close_mongo_connection, get_database
from routers import projects_router, assets_router, clips_router, voiceover_router, export_router

load_dotenv()

SESSION_COOKIE_NAME = "session_id"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await connect_to_mongo()
    yield
    # Shutdown
    await close_mongo_connection()


app = FastAPI(
    title="MCHacks 2026 Video Editor API",
    description="API for video editing with clips, voiceover, and export",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def session_middleware(request: Request, call_next):
    """Ensure session cookie is set for anonymous users."""
    # Get or create session ID BEFORE processing request
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    is_new_session = False

    if not session_id:
        session_id = str(uuid.uuid4())
        is_new_session = True

    # Store session_id in request state for access in routes
    request.state.session_id = session_id

    response = await call_next(request)

    # Set cookie if it was newly created
    if is_new_session:
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            secure=os.getenv("ENV", "development") == "production",
            samesite="lax",
            max_age=60 * 60 * 24 * 30,  # 30 days
        )

    return response


# Include routers
app.include_router(projects_router)
app.include_router(assets_router)
app.include_router(clips_router)
app.include_router(voiceover_router)
app.include_router(export_router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "MCHacks 2026 Video Editor API"}


@app.get("/health")
async def health():
    """Detailed health check."""
    db = get_database()
    db_ok = db is not None
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }
