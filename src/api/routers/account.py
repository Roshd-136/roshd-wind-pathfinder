"""
Account Router — GET /account, PUT /account, GET /account/preferences, PUT /account/preferences,
GET /account/history, DELETE /account.

User account management and preferences.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/account", tags=["account"])

# Mock current user dependency (in production: extract from JWT)
async def get_current_user_id() -> str:
    return "dev-user-123"  # TODO: extract from JWT auth


class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    name: str
    created_at: str
    last_login_at: str | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    email: EmailStr | None = None


class Preferences(BaseModel):
    language: Literal["fa", "en"] = "fa"
    units: Literal["metric", "imperial"] = "metric"
    map_style: Literal["simple", "satellite", "dark", "light"] = "simple"
    default_criterion: Literal["time", "energy", "balanced"] = "balanced"
    default_algorithm: Literal["a_star", "dijkstra"] = "a_star"
    notifications_enabled: bool = True


class RouteHistoryItem(BaseModel):
    route_id: str
    origin: dict  # Coordinate
    destination: dict  # Coordinate
    criterion: Literal["time", "energy", "balanced"]
    algorithm: Literal["a_star", "dijkstra"]
    total_distance_km: float
    estimated_time_hours: float
    created_at: str
    is_saved: bool


# Mock data
_mock_user = {
    "user_id": "dev-user-123",
    "email": "user@example.com",
    "name": "تست کاربر",
    "created_at": "2026-01-01T00:00:00Z",
    "last_login_at": "2026-01-15T10:00:00Z",
}

_mock_preferences = Preferences()

_mock_history: list[RouteHistoryItem] = [
    RouteHistoryItem(
        route_id="route-1",
        origin={"lat": 36.297, "lon": 59.606},
        destination={"lat": 36.215, "lon": 57.678},
        criterion="balanced",
        algorithm="a_star",
        total_distance_km=120.5,
        estimated_time_hours=3.2,
        created_at="2026-01-10T14:30:00Z",
        is_saved=True,
    ),
    RouteHistoryItem(
        route_id="route-2",
        origin={"lat": 35.689, "lon": 51.389},
        destination={"lat": 36.297, "lon": 59.606},
        criterion="time",
        algorithm="a_star",
        total_distance_km=450.0,
        estimated_time_hours=8.5,
        created_at="2026-01-12T09:15:00Z",
        is_saved=False,
    ),
]


@router.get("", response_model=UserProfile)
async def get_profile(user_id: str = Depends(get_current_user_id)):
    """Get current user's profile."""
    if user_id != _mock_user["user_id"]:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(**_mock_user)


@router.put("", response_model=UserProfile)
async def update_profile(update: UserUpdate, user_id: str = Depends(get_current_user_id)):
    """Update user profile."""
    if user_id != _mock_user["user_id"]:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        _mock_user[field] = value
    return UserProfile(**_mock_user)


@router.get("/preferences", response_model=Preferences)
async def get_preferences(user_id: str = Depends(get_current_user_id)):
    """Get user preferences."""
    return _mock_preferences


@router.put("/preferences", response_model=Preferences)
async def update_preferences(update: Preferences, user_id: str = Depends(get_current_user_id)):
    """Update user preferences."""
    global _mock_preferences
    _mock_preferences = update
    return _mock_preferences


@router.get("/history", response_model=list[RouteHistoryItem])
async def get_route_history(
    limit: int = 50,
    offset: int = 0,
    user_id: str = Depends(get_current_user_id),
):
    """Get user's route calculation history."""
    return _mock_history[offset : offset + limit]


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(user_id: str = Depends(get_current_user_id)):
    """Delete user account (irreversible)."""
    # In production: cascade delete all user data
    pass
