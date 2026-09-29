"""خطاهای لایه بک‌اند — مطابق schemaهای ``Error`` و ``ValidationErrorBody`` در OpenAPI."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ApiError", "ValidationFailed", "NotFound", "NoFeasiblePath", "DataUnavailable"]


class ApiError(Exception):
    """خطای عمومی API با کد HTTP و کد ماشین‌خوان."""

    status = 400
    code = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status

    def to_body(self, request_id: str) -> dict:
        return {"code": self.code, "message": self.message, "request_id": request_id}


@dataclass
class _Issue:
    field: str
    issue: str


class ValidationFailed(ApiError):
    """ورودی نامعتبر (HTTP 422) همراه با فهرست فیلد/مشکل."""

    status = 422
    code = "validation_error"

    def __init__(self, issues: list[tuple[str, str]]) -> None:
        super().__init__("Request validation failed.")
        self.issues = [_Issue(f, i) for f, i in issues]

    def to_body(self, request_id: str) -> dict:
        body = super().to_body(request_id)
        body["details"] = [{"field": i.field, "issue": i.issue} for i in self.issues]
        return body


class NotFound(ApiError):
    status = 404
    code = "not_found"


class NoFeasiblePath(ApiError):
    """هیچ مسیر عبوری روی هیچ لایه‌ای پیدا نشد (ورودی معتبر ولی غیرقابل‌حل)."""

    status = 422
    code = "no_feasible_path"


class DataUnavailable(ApiError):
    """داده باد در دسترس نیست (HTTP 503)."""

    status = 503
    code = "wind_data_unavailable"
