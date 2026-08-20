"""FastAPI application entry point for Telegram Mini App Backend."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.routes.chats import router as chats_router
from api.routes.database import router as database_router
from api.routes.stats import router as stats_router
from core.database import init_db, close_db
from core.logger import logger
from core.redis_client import redis_manager
from services.ai.client import ai_dispatcher
from services.ai.normalizer import TextSanitizer


class ScanRequest(BaseModel):
    """Payload for interactive text scanning."""

    text: str
    user_info: str = "MiniApp interactive scan"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database and redis connections."""
    logger.info("Initializing API application services...")
    await init_db()
    await redis_manager.get_client()
    yield
    logger.info("Shutting down API application services...")
    await redis_manager.close()
    await close_db()


app = FastAPI(
    title="TelegramWarden Mini App API",
    description="Backend API for TelegramWarden Group Moderation Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Telegram WebApp
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(chats_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(database_router, prefix="/api")


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring."""
    return {"status": "ok", "service": "TelegramWarden API"}


@app.post("/api/scan", tags=["Scanner"])
async def scan_text_endpoint(payload: ScanRequest):
    """Interactive text scanner for WebApp and Direct Messages."""
    sanitized = TextSanitizer.sanitize(payload.text)
    verdict = await ai_dispatcher.analyze_message(
        message_text=sanitized.clean_text,
        user_info=payload.user_info,
    )
    return {
        "is_violation": verdict.is_violation,
        "category": verdict.category.value,
        "confidence": verdict.confidence,
        "suggested_action": verdict.suggested_action.value,
        "reason": verdict.reason,
    }


# Serve Mini App HTML
WEBAPP_INDEX_PATH = Path("webapp/index.html")


@app.get("/", response_class=HTMLResponse, tags=["WebApp"])
@app.get("/app", response_class=HTMLResponse, tags=["WebApp"])
async def serve_mini_app():
    """Serve Telegram Mini App SPA."""
    if WEBAPP_INDEX_PATH.exists():
        return FileResponse(str(WEBAPP_INDEX_PATH))
    return HTMLResponse("<h1>TelegramWarden Mini App is loading...</h1>")


if Path("webapp").exists():
    app.mount("/static", StaticFiles(directory="webapp"), name="static")
