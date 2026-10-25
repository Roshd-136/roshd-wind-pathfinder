"""
Points Router — GET/POST /points, GET/PUT/DELETE /points/{pointId}.

User-saved waypoints/favorites.
"""
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/points", tags=["points"])


class PointBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    coordinate: "Coordinate"
    type: Literal["waypoint", "favorite", "home", "work"] = "waypoint"
    notes: str | None = None


class Coordinate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PointCreate(PointBase):
    pass


class PointUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    type: Literal["waypoint", "favorite", "home", "work"] | None = None
    notes: str | None = None


class Point(PointBase):
    point_id: str
    created_at: str
    updated_at: str


# Mock in-memory storage
_points: dict[str, Point] = {}


@router.get("", response_model=list[Point])
async def list_points(
    type: Literal["waypoint", "favorite", "home", "work"] | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List user's saved points with optional filtering."""
    results = list(_points.values())
    if type:
        results = [p for p in results if p.type == type]
    return results[offset : offset + limit]


@router.post("", response_model=Point, status_code=status.HTTP_201_CREATED)
async def create_point(point: PointCreate):
    """Create a new saved point."""
    now = datetime.utcnow().isoformat() + "Z"
    new_point = Point(
        point_id=str(uuid4()),
        created_at=now,
        updated_at=now,
        **point.model_dump(),
    )
    _points[new_point.point_id] = new_point
    return new_point


@router.get("/{point_id}", response_model=Point)
async def get_point(point_id: str):
    """Get a specific point by ID."""
    point = _points.get(point_id)
    if not point:
        raise HTTPException(status_code=404, detail="Point not found")
    return point


@router.put("/{point_id}", response_model=Point)
async def update_point(point_id: str, update: PointUpdate):
    """Update a saved point."""
    point = _points.get(point_id)
    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(point, field, value)
    point.updated_at = datetime.utcnow().isoformat() + "Z"
    return point


@router.delete("/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_point(point_id: str):
    """Delete a saved point."""
    if point_id not in _points:
        raise HTTPException(status_code=404, detail="Point not found")
    del _points[point_id]
