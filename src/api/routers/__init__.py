"""
API Routers Package — FastAPI route modules.

Each router implements a tag from api/openapi.yaml:
- routes: /v1/routes*
- wind_layers: /v1/wind-layers*
- points: /v1/points*
- algorithms: /v1/algorithms*
- auth: /v1/auth*
- account: /v1/account*
"""
from . import account, algorithms, auth, points, routes, wind_layers

__all__ = [
    "routes",
    "wind_layers",
    "points",
    "algorithms",
    "auth",
    "account",
]
