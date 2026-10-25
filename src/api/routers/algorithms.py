"""
Algorithms Router — GET /algorithms, GET /algorithms/{algorithmId}, GET /algorithms/criteria.

Information about available routing algorithms and optimization criteria.
متادیتا با موتور واقعی هم‌راستاست: چهار الگوریتم (``a_star``/``dijkstra``/
``smooth``/``wind_riding``) و پنج معیار (``cost.CRITERIA``) — پیش‌تر فقط
دو الگوریتم و سه معیار اعلام می‌شد و بقیهٔ توان موتور از قرارداد API مخفی بود.
"""
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from pathfinding.cost import CRITERIA

router = APIRouter(prefix="/algorithms", tags=["algorithms"])

AlgorithmId = Literal["a_star", "dijkstra", "smooth", "wind_riding"]
CriterionId = Literal["time", "energy", "balanced", "distance", "safety"]


class AlgorithmInfo(BaseModel):
    id: AlgorithmId
    name: str
    description: str
    supports_async: bool
    supports_multi_layer: bool
    typical_duration_ms: int


class CriterionInfo(BaseModel):
    id: CriterionId
    name: str
    description: str
    weight_range: list[float] = Field(..., min_length=2, max_length=2)


_ALGORITHMS = [
    AlgorithmInfo(
        id="a_star",
        name="A* (A-Star)",
        description="Heuristic-guided search, faster for point-to-point routing with good heuristic",
        supports_async=True,
        supports_multi_layer=True,
        typical_duration_ms=150,
    ),
    AlgorithmInfo(
        id="dijkstra",
        name="Dijkstra",
        description="Guaranteed optimal, explores uniformly — better for multi-destination or when heuristic is unreliable",
        supports_async=True,
        supports_multi_layer=True,
        typical_duration_ms=400,
    ),
    AlgorithmInfo(
        id="smooth",
        name="Smoothed A*",
        description="A* on the graph followed by corner fillets and curvature relaxation of the polyline",
        supports_async=True,
        supports_multi_layer=True,
        typical_duration_ms=300,
    ),
    AlgorithmInfo(
        id="wind_riding",
        name="Wind Riding",
        description="Plans a glide-heavy route on continuous wind fields outside the graph; falls back to graph A* on the selected band when no plan fits",
        supports_async=True,
        supports_multi_layer=True,
        typical_duration_ms=600,
    ),
]

_CRITERIA = [
    CriterionInfo(
        id="time",
        name="Fastest Time",
        description="Minimize total travel time regardless of fuel/energy cost",
        weight_range=[0.0, 1.0],
    ),
    CriterionInfo(
        id="energy",
        name="Minimum Energy",
        description="Minimize fuel/energy consumption, may take longer route",
        weight_range=[0.0, 1.0],
    ),
    CriterionInfo(
        id="balanced",
        name="Balanced (Time + Energy)",
        description="Weighted combination of time and energy — configurable via weights",
        weight_range=[0.0, 1.0],
    ),
    CriterionInfo(
        id="distance",
        name="Shortest Distance",
        description="Minimize flown distance only — wind is ignored in the weight",
        weight_range=[0.0, 1.0],
    ),
    CriterionInfo(
        id="safety",
        name="Safety",
        description="Energy cost plus an extra penalty on headwind legs",
        weight_range=[0.0, 1.0],
    ),
]

# گارد هم‌راستایی: اگر معیار تازه‌ای به موتور اضافه شد ولی متادیتا فراموش شد،
# همین‌جا می‌شکند نه در قرارداد API.
assert set(CRITERIA) == {c.id for c in _CRITERIA}, "cost.CRITERIA and metadata drift"


@router.get("", response_model=list[AlgorithmInfo])
async def list_algorithms():
    """List all available routing algorithms with metadata."""
    return _ALGORITHMS


@router.get("/criteria", response_model=list[CriterionInfo], tags=["algorithms"])
async def list_criteria():
    """List all available optimization criteria."""
    return _CRITERIA


@router.get("/{algorithm_id}", response_model=AlgorithmInfo)
async def get_algorithm(algorithm_id: AlgorithmId):
    """Get detailed info for a specific algorithm."""
    algo = next((a for a in _ALGORITHMS if a.id == algorithm_id), None)
    if not algo:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Algorithm not found")
    return algo
