from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError  # FIX 💡-4: import DB error
from app.api.routes import auth, user, trip, day_plan, activity, budget, location, ai_chat
from app.core.config import settings

app = FastAPI(title="Smart Travel Planner API", version="1.0.0")


# ─── Global Exception Handlers ────────────────────────────────────────────────
# Wrap mọi lỗi theo format { status_code, message, data } như API spec yêu cầu

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "message": exc.detail,
            "data": None,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Pydantic v2: exc.errors() có thể chứa ctx={"error": ValueError(...)}
    # ValueError không JSON-serializable → phải chuyển sang str trước
    def _sanitize(errors: list) -> list:
        sanitized = []
        for err in errors:
            e = dict(err)
            if "ctx" in e and isinstance(e["ctx"].get("error"), Exception):
                e["ctx"] = {**e["ctx"], "error": str(e["ctx"]["error"])}
            sanitized.append(e)
        return sanitized

    return JSONResponse(
        status_code=422,
        content={
            "status_code": 422,
            "message": "Validation error",
            "data": {"detail": _sanitize(exc.errors())},
        },
    )


# FIX 💡-4: bắt lỗi DB — trả về đúng format thay vì unhandled 500 stack trace
@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={
            "status_code": 500,
            "message": "Lỗi database, vui lòng thử lại sau",
            "data": None,
        },
    )


# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:8100"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/api")
app.include_router(user.router, prefix="/api")
app.include_router(trip.router, prefix="/api")
app.include_router(day_plan.day_router, prefix="/api")
app.include_router(activity.activity_router, prefix="/api")
app.include_router(budget.router, prefix="/api")
app.include_router(location.router, prefix="/api")
app.include_router(ai_chat.router, prefix="/api")


@app.get("/")
def root():
    from app.schemas.user import BaseResponse
    return BaseResponse(
        status_code=200,
        message="Smart Travel Planner API is running",
        data=None,
    )
