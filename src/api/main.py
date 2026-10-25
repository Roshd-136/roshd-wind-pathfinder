"""
Roshd Wind Pathfinder — FastAPI Application Entry Point.

This module creates the FastAPI app with all routers mounted per the OpenAPI spec.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routers import account, algorithms, auth, points, routes, wind_layers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize any resources (DB connections, cache, etc.)
    yield
    # Shutdown: cleanup resources


app = FastAPI(
    title="Roshd Wind Pathfinder API",
    description="Wind-aware maritime/air route optimization API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend (Vite dev server + Tauri)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite dev
        "http://127.0.0.1:5173",      # Vite dev (loopback IP form)
        "http://localhost:4173",      # Vite preview
        "http://127.0.0.1:4173",      # Vite preview (loopback IP form)
        "tauri://localhost",          # Tauri desktop
        "https://tauri.localhost",    # Tauri with HTTPS
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers with /v1 prefix per OpenAPI spec
app.include_router(routes.router, prefix="/v1")
app.include_router(wind_layers.router, prefix="/v1")
app.include_router(points.router, prefix="/v1")
app.include_router(algorithms.router, prefix="/v1")
app.include_router(auth.router, prefix="/v1")
app.include_router(account.router, prefix="/v1")


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    """خطاهای منطقِ مسیریابی (مثل «در این باند مسیر پروازپذیری نیست») ۴۰۰
    برگردانند، نه ۵۰۰ — پیام فارسیِ موتور همین‌جا به `detail` کلاینت می‌رسد."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancers / monitoring."""
    return {"status": "ok", "service": "roshd-wind-pathfinder"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
