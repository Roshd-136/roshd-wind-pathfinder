"""
Roshd Wind Pathfinder — FastAPI Application Entry Point.

This module creates the FastAPI app with all routers mounted per the OpenAPI spec.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
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


# پیام‌های دامنهٔ عرض/طول جغرافیایی — کامنت ۱۳ «کامنت‌های نرم‌افزار»: کاربر
# پیام خام «Input should be less than or equal to 180» می‌دید و علت را
# نمی‌شناخت. کلید = آخرین جزء `loc` خطای Pydantic (نام فیلد).
_COORDINATE_RANGE_MESSAGES: dict[str, str] = {
    "lat": "عرض جغرافیایی (lat) باید در بازهٔ −۹۰ تا ۹۰ درجه باشد",
    "lon": "طول جغرافیایی (lon) باید در بازهٔ −۱۸۰ تا ۱۸۰ درجه باشد",
}
# فقط نقضِ دامنه ترجمه شود — خطای «فیلد غایب» پیام استاندارد خود را نگه دارد.
_RANGE_ERROR_TYPES = {"less_than_equal", "greater_than_equal"}


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """خطاهای اعتبارسنجی ۴۲۲ با **همان ساختار فهرستیِ استاندارد** `detail`
    برگردند (تا هیچ کلاینتی نشکند)؛ فقط پیامِ خطاهای دامنهٔ عرض/طول به
    فارسیِ خوانا با ذکر مقدار واردشده ترجمه می‌شود. پیام سایر خطاها
    دست‌نخورده می‌ماند."""
    errors = []
    for error in exc.errors():
        loc = [str(item) for item in error.get("loc", ())]
        field = next((f for f in reversed(loc) if f in _COORDINATE_RANGE_MESSAGES), None)
        if field is not None and error.get("type") in _RANGE_ERROR_TYPES:
            value = str(error.get("input", ""))[:40]
            message = _COORDINATE_RANGE_MESSAGES[field]
            if value:
                message += f"؛ مقدار واردشده {value} است"
            message += (
                " — اگر مختصات را دستی یا کپی وارد کرده‌اید، "
                "ترتیب عرض/طول و فرمت آن را بررسی کنید."
            )
            error = {**error, "msg": message}
        errors.append(error)
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)},
    )


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for load balancers / monitoring."""
    return {"status": "ok", "service": "roshd-wind-pathfinder"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
