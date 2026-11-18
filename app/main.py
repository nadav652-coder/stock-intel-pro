"""
FastAPI Main Application Entry Point.
Sets up middlewares, routes, static asset mounts and exception handlers.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.api.routes import router
from app.core.config import settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="מערכת חכמה לניתוח מניות, חיזוי ביצועי השקעות ואופטימיזציה של תיקי השקעות"
)

# Enable CORS for local and public API accessibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Security and Cache Headers Middleware
@app.middleware("http")
async def add_security_and_cache_headers(request, call_next):
    response = await call_next(request)
    
    # 1. Essential Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    
    # 2. Prevent caching of volatile local static assets during rapid updates
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
    return response

# Mount Static Files (CSS, JS)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include API and UI routes
app.include_router(router)
