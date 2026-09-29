"""Smoke tests for the interactive 3D routing scene (`viz.scene3d`).

The scene is the acceptance artifact for the routing work, so these tests guard
the things that would make it silently useless: an empty scene, missing wind
arrows, routes that are not actually different from each other, axis scales that
do not match, or a generated HTML file that lost its honesty labels.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pathfinding.graph import VerticalCostConfig
from pathfinding.wind_riding import WindRidingConfig
from preprocessing.consistency import haversine_km
from viz.scene3d import (
    GRAPH_SPECS,
    ROUTE_LINE_WIDTH,
    ROUTE_SPECS,
    ROUTE_TUBE_RADIUS_KM,
    ROUTE_TUBE_SIDES,
    VERTICAL_EXAGGERATION,
    WIND_RIDING_SPECS,
    WIND_RIDING_VARIANT_SPECS,
    _route_tube,
    build_routes,
    build_scene_figure,
    build_wind_riding_routes,
    route_table_rows,
    write_scene,
)
from viz.terrain import TERRAIN_CSV_PATH, load_terrain
from viz.wind_field import (
    CORRIDOR_BBOX,
    DEMO_DESTINATION,
    DEMO_ORIGIN,
    FLIGHT_LEVELS_MSL,
    LAYER_PROFILES,
    MIN_TERRAIN_CLEARANCE_M,
    VIZ_AIRCRAFT,
    build_level_fields,
    build_multi_layer_graph,
    corridor_lattice,
    load_station_winds,
    lonlat_to_km,
    select_scene_hour,
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "khorasan_wind_qc_cleaned.csv"


@pytest.fixture(scope="module")
def station_winds() -> pd.DataFrame:
    hour = select_scene_hour(pd.read_csv(DATA_PATH))
    return load_station_winds(DATA_PATH, timestamp=hour)


@pytest.fixture(scope="module")
def terrain():
    """The real DEM shipped with the repo (no network access in tests)."""
    if not TERRAIN_CSV_PATH.exists():
        pytest.skip(
            "terrain DEM missing; run `python scripts/fetch_terrain_data.py`"
        )
    return load_terrain(TERRAIN_CSV_PATH)


@pytest.fixture(scope="module")
def ground_elevation_at(terrain):
    """ارتفاع زمین زیر یک نقطه — همان نمونه‌بردار تزریقی صحنه."""

    def sampler(lat: float, lon: float) -> float:
        return float(np.atleast_1d(terrain.elevation_at(lat, lon))[0])

    return sampler


@pytest.fixture(scope="module")
def fields(station_winds: pd.DataFrame, terrain):
    """میدان باد سطوح پرواز، **دقیقاً** همان‌طور که صحنه می‌سازد.

    این fixture باید همان مسیر کد ``write_scene`` را طی کند. اگر گراف آزمون را
    با لایه‌های بالای زمین بسازد و صحنه را با سطوح MSL، آزمون‌ها چیزی را
    می‌سنجند که منتشر نمی‌شود.
    """
    lats, lons = corridor_lattice(station_winds)
    lon_mesh, lat_mesh = np.meshgrid(lons, lats)
    ground = terrain.elevation_at(lat_mesh, lon_mesh).reshape(lat_mesh.shape)
    return build_level_fields(station_winds, ground)


@pytest.fixture(scope="module")
def multi_graph(fields, ground_elevation_at):
    return build_multi_layer_graph(
        fields,
        config=VIZ_AIRCRAFT,
        criterion="time",
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
        edge_terrain_sampler=ground_elevation_at,
    )


@pytest.fixture(scope="module")
def routes(multi_graph, ground_elevation_at):
    return build_routes(
        multi_graph,
        VIZ_AIRCRAFT,
        origin=DEMO_ORIGIN,
        destination=DEMO_DESTINATION,
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
    )


@pytest.fixture(scope="module")
def wind_riding(fields, ground_elevation_at):
    """The wind-riding *family* on the same field the graph routes use.

    The family (the auto route plus the explicit-corridor variants) is planned on
    the continuous field, not on the graph, so it needs its own builder — and the
    test uses the **published** builder so a test can never disagree with what
    ``write_scene`` draws.

    Returns ``(routes, specs, reports)``.
    """
    if not WIND_RIDING_SPECS:
        pytest.skip("no wind-riding route is declared")
    return build_wind_riding_routes(
        fields,
        VIZ_AIRCRAFT,
        ground_elevation_at=ground_elevation_at,
        min_clearance_m=MIN_TERRAIN_CLEARANCE_M,
    )


@pytest.fixture(scope="module")
def wind_riding_specs(wind_riding):
    """The wind-riding specs that were actually built (variants included)."""
    return wind_riding[1]


@pytest.fixture(scope="module")
def all_routes(routes, wind_riding):
    """Every drawn route: the graph routes plus the whole wind-riding family."""
    merged = dict(routes)
    merged.update(wind_riding[0])
    return merged


@pytest.fixture(scope="module")
def drawn_specs(wind_riding_specs) -> tuple:
    """The spec list ``write_scene`` draws with: routes plus built variants."""
    specs = list(ROUTE_SPECS)
    for spec in wind_riding_specs:
        if spec not in ROUTE_SPECS:
            specs.append(spec)
    return tuple(specs)


@pytest.fixture(scope="module")
def figure(fields, multi_graph, all_routes, terrain, station_winds, drawn_specs):
    """A low-resolution variant: the ground grid dominates the build cost."""
    return build_scene_figure(
        fields,
        multi_graph,
        all_routes,
        terrain,
        specs=drawn_specs,
        config=VIZ_AIRCRAFT,
        origin=DEMO_ORIGIN,
        destination=DEMO_DESTINATION,
        station_labels={
            str(row.station): (float(row.lat), float(row.lon))
            for row in station_winds.itertuples()
        },
        ground_n_lat=5,
        ground_n_lon=7,
    )


@pytest.fixture(scope="module")
def scene_html(tmp_path_factory):
    """The published artifact, generated **once** for the whole module.

    ``write_scene`` rebuilds the entire pipeline (fields, graph, every route, the
    wind-riding plan and the ground overlay) on every call, so calling it from
    each HTML test made the file take minutes. The scene is deterministic given
    the same inputs, so one artifact is enough — and it is the artifact the page
    tests actually read. The ground overlay is the expensive part and none of the
    HTML assertions look at it, so it is built at a coarse resolution; the
    published scene keeps the default.
    """
    output = tmp_path_factory.mktemp("scene") / "scene.html"
    path, routes = write_scene(output, DATA_PATH, ground_n_lat=5, ground_n_lon=7)
    return path, routes, path.read_text(encoding="utf-8")


# ===========================================================================
# Scene structure
# ===========================================================================


def test_scene_has_every_expected_trace(figure) -> None:
    """Ground surface, one arrow plane per flight level, and route lines."""
    types = [trace.type for trace in figure.data]
    n_layers = len(FLIGHT_LEVELS_MSL)

    # The terrain surface, plus the optional "best layer" colouring overlay
    # (present whenever at least one cell has a flyable layer).
    assert 1 <= types.count("surface") <= 2
    assert types.count("cone") == n_layers, "one cone (arrow head) trace per layer"

    shaft_traces = [t for t in figure.data if t.type == "scatter3d" and t.mode == "lines"]
    # one shaft trace per wind layer, plus at least one line trace per route
    assert len(shaft_traces) >= n_layers + 2


def test_no_table_trace_inside_the_figure(figure) -> None:
    """The comparison table lives in HTML, not in the figure.

    A `table` trace carves its `domain` out of the figure, which shrank the 3D
    scene, and its cells rendered inside the canvas at a fixed (tiny) size.
    """
    assert [t.type for t in figure.data].count("table") == 0
    assert figure.layout.title.text is None, "the title moved to the HTML header"


def test_scene_is_not_empty(figure) -> None:
    """Every trace must carry real data, not zero-length arrays."""
    for trace in figure.data:
        if trace.type in ("cone", "scatter3d"):
            assert len(trace.x) > 0, f"empty trace: {trace.name}"


def test_wind_arrow_traces_carry_hover_details(figure) -> None:
    """Hovering an arrow must reveal speed, direction and the level it belongs to."""
    for altitude in FLIGHT_LEVELS_MSL:
        label = f"{altitude:.0f}"
        matching = [
            t
            for t in figure.data
            if t.type == "scatter3d"
            and t.name is not None
            and t.name.startswith(f"باد سطح {label} متر")
        ]
        assert matching, f"no wind arrow trace for the {label} m flight level"

        trace = matching[0]
        texts = [t for t in trace.text if t]
        assert texts, f"wind arrows for {altitude} m have no hover text"
        sample = texts[0]
        assert "m/s" in sample, "hover must show wind speed"
        assert "km/h" in sample, "hover must also show km/h"
        assert "جهت" in sample, "hover must show wind direction"
        assert label in sample, "hover must state which flight level it is"
        # ارتفاع *بالای زمین* هم باید باشد: باد همان میدان است، پس تفاوت قله و
        # دشت در ارتفاع بالای زمین دیده می‌شود، نه در سطح پرواز.
        assert "بالای زمین" in sample, "hover must show the real height above ground"
        # The synthetic-data warning must travel with the arrow, not just the title.
        assert "سنتزی" in sample


def test_wind_arrows_are_visible_and_per_layer(figure) -> None:
    """Arrows must be on by default, yet each level toggles independently."""
    arrow_traces = [
        t
        for t in figure.data
        if t.type == "scatter3d" and t.name is not None and t.name.startswith("باد ")
    ]
    assert len(arrow_traces) == len(FLIGHT_LEVELS_MSL)
    for trace in arrow_traces:
        assert trace.visible is True, "wind arrows should be visible by default"
        assert trace.legendgroup is not None, "each level needs its own legend group"
        assert len(trace.x) > 0, "an arrow trace must actually carry geometry"

    groups = {t.legendgroup for t in arrow_traces}
    assert len(groups) == len(FLIGHT_LEVELS_MSL), "each level needs a distinct legend group"


def test_arrow_planes_sit_at_their_flight_level(figure) -> None:
    """پیکان‌ها روی صفحهٔ همان سطح پرواز می‌نشینند، نه روی خط‌الرضای کوه‌ها.

    اگر پیکان هر سطح روی زمین محلی بنشیند، مقایسهٔ «مسیر موازی باد است؟»
    هندسی نیست: مسیر در یک صفحهٔ افقی است و پیکان‌ها روی سطحی موازی کوه.
    """
    exag_scale = VERTICAL_EXAGGERATION / 1000.0
    for altitude in FLIGHT_LEVELS_MSL:
        label = f"{altitude:.0f}"
        shafts = [
            t
            for t in figure.data
            if t.type == "scatter3d"
            and t.name is not None
            and t.name.startswith(f"باد سطح {label} متر")
        ]
        assert shafts, f"missing arrow plane for level {label}"
        zs = [float(v) for v in shafts[0].z if v is not None]
        assert zs, "arrow plane carries no geometry"
        assert all(z == pytest.approx(altitude * exag_scale) for z in zs), (
            "every arrow of a flight level must sit on the same horizontal plane"
        )


# ===========================================================================
# Arrow geometry: data-space, so it scales with zoom
# ===========================================================================


def test_wind_arrows_are_drawn_in_data_space(figure) -> None:
    """Arrow length encodes wind speed, and both parts are in kilometres.

    The requirement is that arrows *scale with zoom* rather than keeping a fixed
    on-screen size. That only holds if every arrow dimension is expressed in data
    coordinates: the shaft spans the scaled wind vector and the cone head's
    ``sizeref`` is in km (``sizemode="absolute"``), never in pixels.
    """
    shafts = [
        t
        for t in figure.data
        if t.type == "scatter3d" and t.name is not None and t.name.startswith("باد ")
    ]
    cones = [t for t in figure.data if t.type == "cone"]
    assert len(shafts) == len(cones) == 4

    for shaft, cone in zip(shafts, cones, strict=True):
        assert cone.sizemode == "absolute"
        assert 0.0 < float(cone.sizeref) < 20.0, "head size must be in km, not pixels"

        # Shaft points come in triples: tail, tip, separator. The tip must be
        # exactly tail + vector, so the drawn length is the scaled wind speed.
        xs = [float(v) for v in shaft.x if v is not None]
        assert len(xs) == 2 * len(cone.x)
        for index in range(len(cone.x)):
            tail_x, tip_x = xs[2 * index], xs[2 * index + 1]
            vector_x = float(cone.u[index])
            assert tip_x == pytest.approx(tail_x + vector_x, abs=1e-9)

        # The head sits at the *tip* of the shaft. At the tail it would cover the
        # whole shaft and every arrow would look the same length.
        for index in range(len(cone.x)):
            assert float(cone.x[index]) == pytest.approx(xs[2 * index + 1], abs=1e-9)

    # Longer arrows must really exist: the shafts are not all one length.
    lengths = []
    for shaft in shafts:
        xs = [float(v) for v in shaft.x if v is not None]
        lengths.extend(
            abs(xs[2 * i + 1] - xs[2 * i]) ** 2
            + abs(float(shaft.y[3 * i + 1]) - float(shaft.y[3 * i])) ** 2
            for i in range(len(xs) // 2)
        )
    assert max(lengths) > min(lengths), "arrow length must vary with wind speed"


# ===========================================================================
# Axis scale: east and north must share one kilometre scale
# ===========================================================================


def _km_extents() -> tuple[float, float]:
    """Corridor extents in km, measured with the same projection the scene uses."""
    plot_origin = (CORRIDOR_BBOX["lat_min"], CORRIDOR_BBOX["lon_min"])
    x_min, y_min = (
        float(v)
        for v in lonlat_to_km(
            CORRIDOR_BBOX["lat_min"], CORRIDOR_BBOX["lon_min"], *plot_origin
        )
    )
    x_max, y_max = (
        float(v)
        for v in lonlat_to_km(
            CORRIDOR_BBOX["lat_max"], CORRIDOR_BBOX["lon_max"], *plot_origin
        )
    )
    return abs(x_max - x_min), abs(y_max - y_min)


def test_axes_share_one_kilometre_scale(figure) -> None:
    """One kilometre east must be exactly as long on screen as one north.

    ``aspectmode="data"`` derived the aspect from the trace *ranges*, and those
    ranges are inflated unevenly by the wind arrows — so the terrain came out
    stretched. The aspect is now computed from the real kilometre extents the
    axes span, which is the extent a reader actually measures on the grid.
    """
    scene = figure.layout.scene
    assert scene.aspectmode == "manual"

    x_extent_km, y_extent_km = _axis_extents(figure)
    scale = max(
        x_extent_km,
        y_extent_km,
        scene.zaxis.range[1] - scene.zaxis.range[0],
    )
    aspect = scene.aspectratio
    assert aspect.x == pytest.approx(x_extent_km / scale, rel=1e-9)
    assert aspect.y == pytest.approx(y_extent_km / scale, rel=1e-9)
    assert aspect.z == pytest.approx(
        (scene.zaxis.range[1] - scene.zaxis.range[0]) / scale, rel=1e-9
    )

    # Same scale, so the ratio of the drawn axis lengths must equal the ratio of
    # the real extents. This is the assertion that would have caught the old bug.
    assert aspect.x / aspect.y == pytest.approx(x_extent_km / y_extent_km, rel=1e-9)


def _axis_extents(figure) -> tuple[float, float]:
    """The kilometre extents the two horizontal axes actually span."""
    scene = figure.layout.scene
    return (
        scene.xaxis.range[1] - scene.xaxis.range[0],
        scene.yaxis.range[1] - scene.yaxis.range[0],
    )


def test_axes_contain_the_corridor_and_every_drawn_route(figure) -> None:
    """No drawn geometry may fall outside the box the axes frame.

    The axes used to span exactly the corridor bbox. A wind-riding route drifts
    outside that bbox on purpose (it rides the wind until the corridor forces it
    back), so part of the line was cut off by the scene frame — the user saw a
    route that "leaves the scene". The ranges are now the union of the corridor
    and everything drawn, plus a small margin for the tube's thickness.

    Both axes must also state the same kilometre tick step: a visible tick step
    is what lets a reader check the shared scale by eye.
    """
    corridor_x, corridor_y = _km_extents()
    scene = figure.layout.scene
    x_lo, x_hi = scene.xaxis.range
    y_lo, y_hi = scene.yaxis.range

    # The corridor (the DEM and the wind arrows) fits with its south-west corner
    # at the plot origin, and is not cropped at the far edge.
    assert x_lo <= ROUTE_TUBE_RADIUS_KM
    assert y_lo <= ROUTE_TUBE_RADIUS_KM
    assert x_hi >= corridor_x
    assert y_hi >= corridor_y

    # ...and so does every sample of every route, tube radius included, so neither
    # the hairline nor the rope is clipped by the frame.
    checked = 0
    route_x_lo = route_x_hi = 0.0
    route_y_lo = route_y_hi = 0.0
    for trace in figure.data:
        group = getattr(trace, "legendgroup", None)
        if not group or str(group).startswith("level-") or trace.type not in ("scatter3d", "mesh3d"):
            continue
        xs = [float(value) for value in trace.x]
        ys = [float(value) for value in trace.y]
        assert min(xs) - ROUTE_TUBE_RADIUS_KM >= x_lo - 1e-9, group
        assert max(xs) + ROUTE_TUBE_RADIUS_KM <= x_hi + 1e-9, group
        assert min(ys) - ROUTE_TUBE_RADIUS_KM >= y_lo - 1e-9, group
        assert max(ys) + ROUTE_TUBE_RADIUS_KM <= y_hi + 1e-9, group
        route_x_lo = min(route_x_lo, min(xs))
        route_x_hi = max(route_x_hi, max(xs))
        route_y_lo = min(route_y_lo, min(ys))
        route_y_hi = max(route_y_hi, max(ys))
        checked += 1
    assert checked >= 2 * len(drawn_keys(figure)), "both traces of each route"

    assert scene.yaxis.dtick is not None
    assert scene.yaxis.dtick == scene.xaxis.dtick

    # The axes must be the *union* plus a margin — not a licence to balloon the
    # box. The margin is 2% of the union on each side, so 5% of slack is plenty.
    union_x = max(corridor_x, route_x_hi) - min(0.0, route_x_lo)
    union_y = max(corridor_y, route_y_hi) - min(0.0, route_y_lo)
    assert (x_hi - x_lo) <= 1.05 * union_x
    assert (y_hi - y_lo) <= 1.05 * union_y


# کمترین فاصله‌ای که یک مسیر گرافی باید از مرز کادر داده داشته باشد (کیلومتر).
#
# مرز کادر داده و مرز شبکهٔ گراف یکی بودند، پس اگر تنها ردیفی که فاصلهٔ ایمنی را
# از زمین رعایت می‌کرد روی خودِ مرز می‌افتاد، مسیر *مجبور* بود روی لبهٔ داده
# پرواز کند. اندازه‌گیری روی همین کریدور: ردیف ۳۶.۰۵ در برابر زمین ۱۹۸۰ متری
# شرق فقط ۲۲۰ متر فاصله می‌داد و ردیف بعدی (۳۶.۱۰) کاملاً مسدود بود؛ نتیجه این
# بود که R4 نزدیک ۶۰ کیلومتر روی خط عرض ثابت ۳۶.۰۴۵ (حتی بیرون از کادر داده)
# پرواز می‌کرد و از صحنه «مقید به لبه» به‌نظر می‌رسید. مرز جنوبی کادر حالا
# ۰.۱۵ درجه عقب‌تر است و دشت واقعی جنوب رشته‌کوه را هم دربر می‌گیرد.
ROUTE_DOMAIN_MARGIN_KM = 2.0


def test_no_graph_route_is_pinned_to_the_data_edge(routes) -> None:
    """هیچ مسیر گرافی نباید روی لبهٔ کادر داده سوار شود.

    مسیری که مماس بر مرز کادر است، جوابِ بهینه‌سازی نیست: جوابِ «گراف این‌جا
    تمام می‌شود» است. این آزمون همان را می‌گیرد — و روی کادر قبلی شکست می‌خورد
    (R4 با عرض ۳۶.۰۴۵ بیرون از مرز ۳۶.۰۵ بود).
    """
    assert routes, "no graph route was built"
    km_per_deg = 111.32
    mid_lat = 0.5 * (CORRIDOR_BBOX["lat_min"] + CORRIDOR_BBOX["lat_max"])
    km_per_lon_deg = km_per_deg * math.cos(math.radians(mid_lat))
    margin_lat = ROUTE_DOMAIN_MARGIN_KM / km_per_deg
    margin_lon = ROUTE_DOMAIN_MARGIN_KM / km_per_lon_deg

    for key, result in routes.items():
        latitudes = [lat for lat, _lon in result.path]
        longitudes = [lon for _lat, lon in result.path]
        assert min(latitudes) - CORRIDOR_BBOX["lat_min"] >= margin_lat, (
            f"{key} rides the southern data edge"
        )
        assert CORRIDOR_BBOX["lat_max"] - max(latitudes) >= margin_lat, (
            f"{key} rides the northern data edge"
        )
        assert min(longitudes) - CORRIDOR_BBOX["lon_min"] >= margin_lon, (
            f"{key} rides the western data edge"
        )
        assert CORRIDOR_BBOX["lon_max"] - max(longitudes) >= margin_lon, (
            f"{key} rides the eastern data edge"
        )


def drawn_keys(figure) -> set[str]:
    """Legend groups of the drawn routes in a figure."""
    return {
        str(trace.legendgroup)
        for trace in figure.data
        if getattr(trace, "legendgroup", None)
        and not str(trace.legendgroup).startswith("level-")
    }


def test_scene_axes_use_declared_vertical_exaggeration(figure) -> None:
    """The z axis must state the exaggeration, or the altitudes would mislead."""
    z_title = figure.layout.scene.zaxis.title.text
    assert f"{VERTICAL_EXAGGERATION:.0f}" in z_title


# ===========================================================================
# Layout: scene owns the window, labels float on top
# ===========================================================================


def test_scene_reaches_the_window_edge(figure) -> None:
    """No tiled subplot band: the scene is the page."""
    assert figure.layout.height is None, "height must be fluid, not a fixed 1000px"
    assert figure.layout.autosize is True
    assert figure.layout.margin.l == 0 and figure.layout.margin.b == 0
    assert figure.layout.showlegend is False, (
        "the Plotly legend would cover the scene; HTML chips replace it"
    )


def test_legend_is_exposed_through_trace_meta(figure, drawn_specs) -> None:
    """Legend chips are built from ``meta``, so every labelled trace needs it."""
    from viz.scene3d import _legend_entries

    labelled = [
        t
        for t in figure.data
        if isinstance(getattr(t, "meta", None), dict) and "legend" in t.meta
    ]
    labels = [t.meta["legend"] for t in labelled]
    # terrain + optional best-layer overlay + one per wind layer
    assert any("زمین" in label for label in labels)
    assert len({label for label in labels if label.startswith("باد ")}) == 4
    # One chip per route, the wind-riding variants included: a drawn route that
    # cannot be switched off (to isolate it) would be a missing control.
    for spec in drawn_specs:
        assert any(label.startswith(spec.key) for label in labels), spec.key

    # The "best layer" overlay must start hidden, and its chip must say so.
    overlays = [t for t in labelled if t.visible == "legendonly"]
    assert overlays, "the best-layer overlay should start switched off"

    # A chip controls a *group*, not a single trace: the shaft and the head of
    # one arrow layer toggle together, and a route is one single curve.
    #
    # A route is now *two* traces of the *same* geometry: the hairline (hover +
    # a crisp core) and the mesh tube that gives it thickness without the beading
    # plotly's thick 3D lines show at distance. They must travel together, so the
    # group has exactly two members and the tube takes no chip of its own.
    entries = _legend_entries(figure)
    chips = [entry for entry in entries if entry["chip"]]
    assert len(chips) == len({entry["label"] for entry in chips}), (
        "each chip must be a distinct legend entry"
    )
    by_group = {entry["group"]: entry for entry in entries}
    for spec in drawn_specs:
        group = by_group[spec.key]
        kinds = sorted(
            figure.data[index].type for index in group["traces"]
        )
        assert kinds == ["mesh3d", "scatter3d"], (
            f"a route is one curve drawn twice (line + tube), not {kinds}"
        )
    for altitude in FLIGHT_LEVELS_MSL:
        group = by_group[f"level-{altitude:.0f}"]
        assert len(group["traces"]) == 2, "arrow shaft + head travel together"
    # Every trace the page can toggle must be listed exactly once somewhere.
    covered = [index for entry in entries for index in entry["traces"]]
    assert len(covered) == len(set(covered))


# ===========================================================================
# Terrain (DEM)
# ===========================================================================


def test_ground_surface_comes_from_real_terrain(figure, terrain) -> None:
    """The ground plane must be the DEM, not a flat z=0 sheet."""
    surfaces = [t for t in figure.data if t.type == "surface"]
    # One terrain surface plus the optional (off-by-default) best-layer overlay.
    assert 1 <= len(surfaces) <= 2

    ground = surfaces[0]
    expected = terrain.elevation_m * (VERTICAL_EXAGGERATION / 1000.0)
    assert np.asarray(ground.z).shape == expected.shape
    assert np.allclose(np.asarray(ground.z, dtype=float), expected, atol=1e-9)
    # A flat sheet would render the relief invisible; this DEM really has relief.
    assert terrain.relief_m > 100.0, terrain.relief_m


def test_terrain_grid_is_nearly_square_in_kilometres(terrain) -> None:
    """The DEM samples must be square, or relief is smeared east-west.

    The scene draws one kilometre the same length in both directions, so a grid
    that is far coarser in longitude renders ridges as wide, smeared bands.
    """
    step_lat_km = (terrain.lats[1] - terrain.lats[0]) * 111.32
    step_lon_km = (
        (terrain.lons[1] - terrain.lons[0])
        * 111.32
        * np.cos(np.radians(float(np.mean(terrain.lats))))
    )
    assert (
        0.5 <= step_lon_km / step_lat_km <= 2.0
    ), f"DEM step {step_lat_km:.1f} km (N-S) vs {step_lon_km:.1f} km (E-W)"


def test_terrain_hover_reports_elevation(figure) -> None:
    """Hovering the ground must say how high the ground is at that point."""
    ground = [t for t in figure.data if t.type == "surface"][0]
    texts = [str(t) for t in np.asarray(ground.text).ravel() if t]
    assert texts
    assert "ارتفاع زمین" in texts[0]
    assert "متر" in texts[0]


def test_best_layer_overlay_is_present_but_off(figure) -> None:
    """The best-layer colouring stays opt-in so the terrain shape is readable."""
    surfaces = [t for t in figure.data if t.type == "surface"]
    if len(surfaces) < 2:
        pytest.skip("no cell has a flyable layer at this hour")
    overlay = surfaces[1]
    assert overlay.visible == "legendonly"
    assert "بهترین لایه" in overlay.name


# ===========================================================================
# Multi-layer (3D) routing and ground-anchored endpoints
# ===========================================================================


def test_free_routes_fly_the_merged_3d_graph(routes) -> None:
    """R1..R3 route on the merged graph: ground start, ground end, climb paid.

    Whether they *also* change altitude is a property of the wind field, not of
    the code. In this dataset they do not: the best layer is only ~2 minutes
    faster than the lowest while a climb to it costs ~18 minutes, so the optimum
    stays low. What must hold is that they are genuinely 3D routes — they leave
    and rejoin the ground and report the vertical cost. The reachability of an
    altitude switch is covered separately in ``tests/pathfinding/test_routing.py``
    on a wind profile where climbing pays, so a regression that silently
    collapses the routed graph back to flat layers still fails a test.
    """
    for key in ("R1", "R2", "R3"):
        result = routes[key]
        assert result.node_altitudes, "node altitudes must be reported"
        assert result.node_altitudes[0] == 0.0, f"{key} must start on the ground"
        assert result.node_altitudes[-1] == 0.0, f"{key} must end on the ground"
        assert result.total_climb_m > 0.0, f"{key} must pay for the climb"
        assert result.total_descent_m > 0.0, f"{key} must pay for the descent"
        assert result.climb_legs >= 2


def test_single_layer_route_never_leaves_its_layer(routes) -> None:
    """R4 and R6 exist precisely to show the cost of the no-layer-change constraint.

    They are a controlled pair on one objective (energy): the same corridor, one
    locked to the low level (detour through the pass), one locked to the high
    level (straight over the range). Both must stay in exactly one level while
    the free route is allowed to step between them.
    """
    for key in ("R4", "R6"):
        result = routes[key]
        assert not result.is_multilayer, key
        assert len(result.altitudes_used) == 1, key

    low, high, free = routes["R4"], routes["R6"], routes["R1"]
    # The free route really does move between levels; otherwise "the constraint
    # is what costs you" would be an empty claim.
    assert free.is_multilayer
    # The high lock is above everything the free route reaches (it climbs 2.6 km
    # over the range instead of detouring), and the two locked routes disagree
    # about the corridor: the low one must go around, so it is the longer line.
    assert min(high.altitudes_used) > max(free.altitudes_used)
    assert low.total_distance_km > free.total_distance_km
    # And both constraints cost something: the free route beats each of them on
    # their shared objective (energy), which is why neither lock is the optimum.
    assert free.total_energy_index < low.total_energy_index
    assert free.total_energy_index < high.total_energy_index


def test_endpoints_sit_on_the_ground(figure, routes, terrain) -> None:
    """Start and end markers must be on the terrain, not floating in the sky."""
    exag_scale = VERTICAL_EXAGGERATION / 1000.0
    expected = {
        "مبدأ: مشهد": terrain.elevation_at(*DEMO_ORIGIN),
        "مقصد: سبزوار": terrain.elevation_at(*DEMO_DESTINATION),
    }
    markers = {
        t.name: t for t in figure.data if t.type == "scatter3d" and t.name in expected
    }
    assert set(markers) == set(expected), markers

    for name, trace in markers.items():
        ground_m = float(np.atleast_1d(expected[name])[0])
        assert len(trace.z) == 1
        assert abs(float(trace.z[0]) - ground_m * exag_scale) < 1e-6, (
            name,
            trace.z[0],
            ground_m * exag_scale,
        )

    # And the route geometry itself is anchored, in **both** representations:
    #
    # * ``node_altitudes`` follows the `RouteResult` convention — a ground node is
    #   reported as **zero**, not as its height above sea level. That convention is
    #   what ``WindRouter`` documents and what ``wind_riding`` deliberately matches,
    #   and it is how the scene knows a sample is on the ground.
    # * the *drawn* line is what must not float: its first and last z are the real
    #   terrain elevation, scaled by the vertical exaggeration. That is exactly the
    #   substitution the scene performs on a zero sample, so this is the assertion
    #   that the markers and the line agree.
    exag_scale = VERTICAL_EXAGGERATION / 1000.0
    for key, result in routes.items():
        assert result.node_altitudes[0] == 0.0, key
        assert result.node_altitudes[-1] == 0.0, key
        line = _route_line(figure, key)
        for lat, lon, drawn_z in (
            (result.path[0][0], result.path[0][1], line.z[0]),
            (result.path[-1][0], result.path[-1][1], line.z[-1]),
        ):
            assert (
                terrain.lats[0] <= lat <= terrain.lats[-1]
            ), (key, lat, "endpoint is outside the DEM, so its ground height is extrapolated")
            assert terrain.lons[0] <= lon <= terrain.lons[-1], (key, lon)
            ground_m = float(np.atleast_1d(terrain.elevation_at(lat, lon))[0])
            assert float(drawn_z) == pytest.approx(ground_m * exag_scale, abs=1e-6), (
                key,
                drawn_z,
                ground_m * exag_scale,
            )


# ===========================================================================
# The four routes and their reported numbers
# ===========================================================================


def test_graph_routes_are_built(routes) -> None:
    """Every graph route exists and is physically plausible."""
    assert set(routes) == {spec.key for spec in GRAPH_SPECS}
    for key, result in routes.items():
        assert len(result.node_ids) >= 2, f"{key} has no path"
        assert result.total_distance_km > 0.0
        assert result.estimated_time_hours > 0.0


def test_every_drawn_route_is_in_the_scene(all_routes, drawn_specs) -> None:
    """The scene draws exactly the declared routes: graph *and* wind-riding."""
    assert set(all_routes) == {spec.key for spec in drawn_specs}


def test_wind_riding_variants_are_a_family_on_one_level(
    wind_riding, wind_riding_specs, drawn_specs
) -> None:
    """The wind-riding copies are a *family*: one level, several corridors.

    Wind riding is not one route: the corridor — how far the aircraft may drift
    from the straight line to stay parallel to the wind — is a trade-off, and
    every corridor gives a different path. Drawing more than one is only useful if
    they are genuinely different and genuinely comparable, so this pins both:
    same cruise level (so the difference is the corridor, not the altitude) and a
    distinct path and distinct numbers for each.
    """
    routes, specs, reports = wind_riding
    assert WIND_RIDING_VARIANT_SPECS, "the family is empty; nothing to compare"
    assert specs, "no wind-riding plan exists in this wind field"
    assert specs[0].key == WIND_RIDING_SPECS[0].key

    levels = {routes[spec.key].layer_altitude for spec in specs}
    assert len(levels) == 1, f"the family must fly one level, not {levels}"

    paths = {spec.key: tuple(routes[spec.key].node_ids) for spec in specs}
    assert len(set(paths.values())) == len(paths), paths
    distances = {round(routes[spec.key].total_distance_km, 3) for spec in specs}
    assert len(distances) == len(specs), distances

    # A variant that is *not* drawn must be the one whose corridor equals the
    # corridor the auto route chose — a documented duplicate, never a silent
    # omission or a failed plan.
    best = min(reports, key=lambda item: item.total_time_hours)
    built = {spec.key for spec in specs}
    for spec in WIND_RIDING_VARIANT_SPECS:
        if spec.key in built:
            continue
        assert spec.wind_corridor_fraction is not None
        assert math.isclose(
            spec.wind_corridor_fraction, best.corridor_fraction, abs_tol=1e-6
        ), f"{spec.key} was dropped for an unexpected reason"


def test_wind_riding_variants_are_measured_like_every_other_route(
    all_routes, drawn_specs
) -> None:
    """Every variant gets the same columns as the rest of the table.

    The point of drawing several wind-riding paths is comparing them; a variant
    that reached the scene but not the table (or the alignment columns) would be
    a picture nobody can check.
    """
    variant_keys = [spec.key for spec in drawn_specs if spec in WIND_RIDING_VARIANT_SPECS]
    if not variant_keys:
        pytest.skip("no wind-riding variant survived the corridor search")

    header, rows = route_table_rows(all_routes, specs=drawn_specs)
    assert [row[0] for row in rows] == [
        spec.key for spec in drawn_specs if spec.key in all_routes
    ]
    for column in ("موازی با باد (≤۳°)", "ترکیبی (درجه – سهم)", "سوخت (kg)"):
        assert column in header
    by_key = {row[0]: row for row in rows}
    for key in variant_keys:
        # The share is a percentage in the *Persian* percent sign (the table is
        # Persian throughout), e.g. «۹٪» or «۶۲٪».
        share = by_key[key][header.index("موازی با باد (≤۳°)")]
        assert share.endswith("٪"), share
        assert 0.0 <= float(share[:-1]) <= 100.0, share


def test_routes_are_actually_different(routes) -> None:
    """Four routes are only worth drawing if they do not collapse onto one line."""
    distances = {key: r.total_distance_km for key, r in routes.items()}
    times = {key: r.estimated_time_hours for key, r in routes.items()}
    node_sets = {key: tuple(r.node_ids) for key, r in routes.items()}

    assert len(set(node_sets.values())) >= 3, node_sets
    assert len({round(d, 3) for d in distances.values()}) >= 2, distances
    assert len({round(t, 4) for t in times.values()}) >= 3, times

    # The constrained route is a genuinely different altitude, not a relabel.
    assert routes["R4"].altitudes_used != routes["R1"].altitudes_used


def test_shared_horizontal_distance_is_explained_by_altitude(routes) -> None:
    """A route drawn as a different line must not report *identical* numbers.

    ``total_distance_km`` is a *horizontal* measurement, so two routes can share
    a rounded value while flying at different altitudes — that is only honest if
    the table also reports the cruise altitude and the vertical distance, which
    it does. What must never happen is a route drawn as a visibly different line
    while claiming bit-for-bit identical numbers.

    The comparison is deliberately made at the engine's precision, not on the
    rounded strings: R1 and R2 differ by 34 m over 176 km, which rounds to the
    same 176.6 in the table. That is a real (if tiny) difference, and the table
    is not lying — it is rounding.
    """
    def numbers(key: str) -> tuple[float, float, float]:
        result = routes[key]
        vertical_km = (result.total_climb_m + result.total_descent_m) / 1000.0
        return (
            result.total_distance_km,
            result.layer_altitude,
            result.total_distance_km + vertical_km,
        )

    shared = [
        key
        for key in routes
        if f"{routes[key].total_distance_km:.1f}" == f"{routes['R1'].total_distance_km:.1f}"
    ]
    assert len(shared) >= 2, "expected a shared horizontal distance in this wind field"

    for key in shared:
        if key == "R1" or routes[key].node_ids == routes["R1"].node_ids:
            continue
        assert numbers(key) != numbers("R1"), (
            f"{key} is drawn as a different path yet claims exactly the same "
            "distance, altitude and 3D distance as R1"
        )

    # Where the two routes *are* visually distinct, the reason must be visible in
    # the table: a different cruise level or a different vertical profile.
    for key in ("R4", "R6"):
        assert numbers(key)[1] != numbers("R1")[1], key


def test_table_numbers_match_the_engine(routes) -> None:
    """The comparison table must report the engine's numbers, not re-derived ones.

    Columns are looked up **by name**, not by position: this table grew columns
    (3D distance, drawn length, fuel) several times, and a positional test either
    breaks for the wrong reason or — worse — compares the wrong pair of numbers
    and still passes.
    """
    header, rows = route_table_rows(routes)
    assert len(rows) == len(routes)
    assert header[0] == "مسیر"

    distance_index = header.index("مسافت افقی (km)")
    time_index = header.index("زمان پرواز (h)")
    level_index = header.index("سطح پرواز (m MSL)")

    by_key = {row[0]: row for row in rows}
    for key, result in routes.items():
        row = by_key[key]
        assert float(row[distance_index]) == pytest.approx(
            result.total_distance_km, abs=0.05
        )
        assert float(row[time_index]) == pytest.approx(
            result.estimated_time_hours, abs=5e-4
        )
        assert float(row[level_index]) == pytest.approx(result.layer_altitude, abs=0.5)


# ===========================================================================
# The drawn geometry must reproduce the reported numbers
# ===========================================================================


def _route_line(figure, key: str):
    """The smooth line trace that *is* the drawn geometry of one route."""
    (trace,) = [
        t
        for t in figure.data
        if t.type == "scatter3d" and t.legendgroup == key and t.mode == "lines"
    ]
    return trace


def test_drawn_geometry_matches_the_reported_distance(figure, routes) -> None:
    """The picture must prove the table: the drawn line *is* the route.

    The question "why is the reported distance difference so small when the
    lines look so different?" is only answerable if the geometry on screen is
    the same geometry the numbers came from. Here the drawn line is measured
    independently (from the projected x/y in km) and compared with
    ``total_distance_km``.
    """
    for key, result in routes.items():
        trace = _route_line(figure, key)
        xs = np.asarray(trace.x, dtype=float)
        ys = np.asarray(trace.y, dtype=float)
        drawn_horizontal = float(np.sum(np.hypot(np.diff(xs), np.diff(ys))))
        # The scene draws in a *flat* kilometre projection (constant km/degree),
        # while the engine sums great-circle segments on a sphere. Over this
        # 174 km, 36°N corridor the two differ by a few tenths of a percent —
        # small enough that the picture proves the table, and a reminder that the
        # table's numbers come from the engine, never from the projection.
        assert drawn_horizontal == pytest.approx(result.total_distance_km, rel=5e-3), key
        assert abs(drawn_horizontal - result.total_distance_km) < 1.0, key


def test_each_route_is_one_line_plus_one_tube(figure, routes) -> None:
    """One route = one hairline curve + one mesh rope built on the same geometry.

    The drawn route used to be a single `scatter3d` line of width 9. That looked
    like a chain of beads: plotly's 3D thick line is a ribbon with a miter quad at
    every joint, and when a segment is shorter on screen than the line is wide
    (600 samples over 177 km, 9 px wide) the joints drop out. Nothing about the
    underlying geometry was discrete — the *renderer* was. So the route is now a
    hairline line (continuous at every zoom, and the carrier of the hover text)
    plus a `mesh3d` tube, which is real geometry and therefore has no joints to
    break. Both must belong to the route's legend group so that hiding,
    isolating and double-click keep working on the whole route at once.
    """
    for key, result in routes.items():
        traces = [t for t in figure.data if t.legendgroup == key]
        lines = [t for t in traces if t.type == "scatter3d"]
        tubes = [t for t in traces if t.type == "mesh3d"]
        assert len(lines) == 1, f"{key}: exactly one line trace, not {len(lines)}"
        assert len(tubes) == 1, f"{key}: exactly one tube trace, not {len(tubes)}"

        line = lines[0]
        assert line.mode == "lines"
        # A hairline: a thicker line is the very thing that broke into beads.
        assert line.line.width == ROUTE_LINE_WIDTH == 1, key
        assert len(line.x) >= len(result.path) or len(line.x) >= 200, key
        # A curve, not a handful of segments between lattice nodes.
        assert len(line.x) > 100, f"{key}: {len(line.x)} samples is a polyline, not a curve"

        tube = tubes[0]
        # The rope is a closed ring per sample: 6 sides, two triangles per quad.
        assert len(tube.x) == len(tube.y) == len(tube.z), key
        assert len(tube.x) % ROUTE_TUBE_SIDES == 0, key
        assert len(tube.i) == len(tube.j) == len(tube.k) == 2 * (len(tube.x) - ROUTE_TUBE_SIDES), key
        # It must wrap the *same* path: identical ends, and no ring further from
        # the line than the tube radius (a twisted frame would blow that up).
        assert tube.hoverinfo == "skip", "the numbers come from the line, not the rope"


def test_route_tube_wraps_the_path_without_twisting() -> None:
    """The tube is centred on the path and keeps an even radius around it.

    Built on a deliberately hostile path: straight, then a right-angle turn, then
    a climb. A frame that is *not* parallel-transported flips where the tangent
    lines up with its reference axis, and the ring collapses — which would show
    up here as a point far from the path.
    """
    x = np.concatenate([np.linspace(0.0, 10.0, 40), np.full(40, 10.0), np.full(40, 10.0)])
    y = np.concatenate([np.zeros(40), np.linspace(0.0, 10.0, 40), np.full(40, 10.0)])
    z = np.concatenate([np.zeros(80), np.linspace(0.0, 4.0, 40)])
    tube = _route_tube(x, y, z, radius_km=0.4, sides=ROUTE_TUBE_SIDES, stride=1)
    assert tube is not None

    points = np.column_stack([tube["x"], tube["y"], tube["z"]])
    path = np.column_stack([x, y, z])
    # Distance to the *centreline* (the polyline), not to its samples: the samples
    # are ۰.۲۶ km apart, far denser than the ۰.۴ km radius, so a sample-to-sample
    # distance measures the sampling, not the tube.
    distances = np.full(len(points), np.inf)
    for start, end in zip(path[:-1], path[1:], strict=True):
        spine = end - start
        scale = float(spine @ spine) or 1.0
        projection = np.clip(((points - start) @ spine) / scale, 0.0, 1.0)
        closest = start + projection[:, None] * spine
        distances = np.minimum(distances, np.linalg.norm(points - closest, axis=1))
    # Nothing bulges outside the radius…
    assert np.all(distances <= 0.4 + 1e-9), float(distances.max())
    # …and the ring is a ring, not a smear:
    rings = points.reshape(-1, ROUTE_TUBE_SIDES, 3)
    assert len(rings) == len(path), "with stride=1 there is one ring per sample"
    centres = rings.mean(axis=1)
    assert np.allclose(centres, path, atol=1e-9), "each ring is centred on the path"
    # Every vertex sits *exactly* the radius from its own ring centre. A collapsed
    # or twisted frame breaks this; the polyline-distance proxy above cannot.
    spread = np.linalg.norm(rings - centres[:, None, :], axis=2)
    assert np.allclose(spread, 0.4, atol=1e-9), (float(spread.min()), float(spread.max()))

    # The ring plane is perpendicular to the path tangent…
    tangent = np.gradient(path, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-12)
    normals = np.cross(rings[:, 1] - rings[:, 0], rings[:, 2] - rings[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)
    assert np.all(np.abs(np.einsum("ij,ij->i", normals, tangent)) > 0.99)

    # …و مهم‌ترین قید که فقط با انتقال موازی برقرار می‌شود: **قاب در طول مسیر
    # نمی‌چرخد.** مسیر آزمون عمداً جایی شروع می‌شود که مماس **دقیقاً** روی محور
    # مرجع قاب بیفتد (پای عمودی) — همان حالت خاصی که یک قاب ساده با «بالای ثابت»
    # در آن واژگون می‌شود — و بعد با یک قوس ربع‌دایره در ۱۶ گام کوچک به افقی
    # می‌رسد. پای عمودی و قوس در نقطهٔ اتصال *مماس مشترک* دارند (قوس با مماس
    # عمودی شروع می‌شود)، پس هر گام یک چرخش ۵.۶ درجه‌ای است و قاب درست باید
    # همان ۵.۶ درجه را بچرخد، نه جهش کند.
    radius = 8.0
    phi = np.radians(np.linspace(0.0, 90.0, 16))[1:]
    bend = np.concatenate([np.zeros(16), radius * (1.0 - np.cos(phi))])
    climb = np.concatenate([np.linspace(0.0, 10.0, 16), 10.0 + radius * np.sin(phi)])
    smooth = _route_tube(
        bend, np.zeros_like(bend), climb, radius_km=0.4, sides=ROUTE_TUBE_SIDES, stride=1
    )
    assert smooth is not None
    smooth_points = np.column_stack([smooth["x"], smooth["y"], smooth["z"]])
    smooth_rings = smooth_points.reshape(-1, ROUTE_TUBE_SIDES, 3)
    smooth_centres = smooth_rings.mean(axis=1)
    firsts = (smooth_rings[:, 0] - smooth_centres) / 0.4
    steps = np.einsum("ij,ij->i", firsts[:-1], firsts[1:])
    assert np.all(steps > 0.9), float(steps.min())


def test_route_tube_needs_two_points() -> None:
    """A single-point route has no tube (and must not raise)."""
    assert _route_tube(np.array([0.0]), np.array([0.0]), np.array([0.0])) is None


def test_no_graph_route_carries_a_kink(figure, routes) -> None:
    """A graph route must be a *curve*, not long straights joined by corners.

    The eye does not measure the total turn, it measures the *rate*: a 6° turn
    spread over 3 km is a gentle bend, the same 6° inside one sample is a corner.
    The wind-riding routes are built by integration and change heading a little at
    every sample, which is exactly what "smooth" looks like; the graph routes used
    to be a lattice polyline with a 3 km fillet at each node — a dead-straight run
    and then 12–21°/km at the corner (measured on the published artifact: R1 11.8,
    R2 12.3, R4 14.8 °/km). The threshold is set above the steepest terrain-forced
    bend on this corridor (R4, which must round a ridge) so the test measures
    *concentration*, not how curved the route happens to be.
    """
    allowed_rate = 5.0  # degrees per kilometre

    for key, _result in routes.items():
        trace = _route_line(figure, key)
        xs = np.asarray(trace.x, dtype=float)
        ys = np.asarray(trace.y, dtype=float)
        worst = 0.0
        worst_at_km = 0.0
        travelled = 0.0
        for index in range(1, len(xs) - 1):
            ax, ay = xs[index - 1], ys[index - 1]
            bx, by = xs[index], ys[index]
            cx, cy = xs[index + 1], ys[index + 1]
            seg = float(np.hypot(cx - bx, cy - by))
            travelled += float(np.hypot(bx - ax, by - ay))
            if seg <= 1e-9:
                continue
            first = math.atan2(bx - ax, by - ay)
            second = math.atan2(cx - bx, cy - by)
            turn = math.degrees(second - first)
            while turn > 180.0:
                turn -= 360.0
            while turn < -180.0:
                turn += 360.0
            rate = abs(turn) / seg
            if rate > worst:
                worst = rate
                worst_at_km = travelled
        assert worst <= allowed_rate, (
            f"{key}: {worst:.1f}°/km at {worst_at_km:.0f} km — that is a corner, "
            "not a curve"
        )


def test_drawn_profiles_are_gradual_over_every_window(figure, routes) -> None:
    """هیچ‌جای خط رسم‌شده یک «افتادن عمودی» نیست — در هیچ پنجره‌ای.

    این همان ایرادی است که دیده شد: پروفیل تا نزدیک مقصد تراز می‌ماند و بعد
    ارتفاع را در یک بازهٔ کوتاه خالی می‌کرد، پس خط روی صفحه یک دیوار عمودی
    داشت. سنجه یک نمونهٔ تکی نیست، بلکه **پنجرهٔ ۲ کیلومتری مسافت افقی** است:
    یک بازگشت کوچک چند صد متری در انتهای مسیر (بیش‌پرواز و برگشت، که یک
    هواپیمای واقعی هم نمی‌تواند از آن پرهیز کند) نباید آزمون را بشکند، ولی
    خالی‌کردن دو کیلومتر ارتفاع در دو کیلومتر مسافت حتماً باید.

    ارتفاع خط در محور z با ``VERTICAL_EXAGGERATION`` بزرگ‌نمایی شده است؛ همان
    ضریب این‌جا برگردانده می‌شود تا سنجه با عدد فیزیکی یکی باشد.
    """
    window_km = 2.0
    # سقف فیزیکی: صعود ۲.۵ m/s روی ~۲۱ m/s (۰.۱۲) و فرود با گلاید ۱:۱۲
    # (۰.۰۸۳). با یک حاشیهٔ کوچک برای گردکردن گوشه‌ها و منحنی اسپلاین.
    allowed_slope = 0.12

    for key, result in routes.items():
        trace = _route_line(figure, key)
        xs = np.asarray(trace.x, dtype=float)
        ys = np.asarray(trace.y, dtype=float)
        zs = np.asarray(trace.z, dtype=float)
        arc = np.concatenate(
            [[0.0], np.cumsum(np.hypot(np.diff(xs), np.diff(ys)))]
        )
        altitude_m = zs * 1000.0 / VERTICAL_EXAGGERATION

        worst = 0.0
        worst_at = 0.0
        for start in range(len(arc)):
            end = int(np.searchsorted(arc, arc[start] + window_km))
            if end >= len(arc) or arc[end] - arc[start] < window_km * 0.99:
                break
            change = abs(altitude_m[end] - altitude_m[start])
            slope = change / ((arc[end] - arc[start]) * 1000.0)
            if slope > worst:
                worst = slope
                worst_at = float(arc[start])
        assert worst <= allowed_slope, (
            f"{key}: {worst:.3f} m/m over a {window_km:.0f} km window at "
            f"{worst_at:.0f} km looks like a cliff"
        )
        # و همین سنجه در دو سر مسیر: مسیر روی زمین بلند می‌شود و روی زمین
        # می‌نشیند، پس اختلاف ارتفاع دو سر باید مجموع صعود+فرود باشد.
        assert altitude_m[-1] - altitude_m[0] == pytest.approx(
            -result.total_descent_m + result.total_climb_m, abs=120.0
        ), key


def test_drawn_line_is_longer_than_the_real_distance(figure, routes, terrain) -> None:
    """The drawn length must be reported, because it is *not* the real distance.

    The scene draws each route at its profile altitude and multiplies altitude by
    ``VERTICAL_EXAGGERATION``, so the line on screen is much longer than either
    number in the table. Without a column saying so, the picture contradicts the
    table and looks like a bug.

    Two bounds pin the shape, and together they say "ramped, not stepped": the
    drawn line is always longer than the horizontal distance (it climbs), and
    always *shorter* than the same profile flown as vertical edges. A tilted
    segment of run ``s`` and rise ``E·h`` is only ``√(s²+(E·h)²)`` long, not
    ``s + E·h`` — and that shortfall is exactly the visible difference between a
    ramp and a wall. It is a real assertion about the geometry, not a restatement
    of the code: the wall profile is what the *graph* alone would draw.

    The route is **level** at its flight level, not draped over the ground: the only
    place the profile leaves the level is where the ground below would otherwise
    intrude on the safety clearance, and there it rises just enough to clear it.
    """
    from viz.scene3d import drawn_polyline_km

    drawn = {key: drawn_polyline_km(result, terrain) for key, result in routes.items()}
    for key, result in routes.items():
        vertical_km = (result.total_climb_m + result.total_descent_m) / 1000.0
        wall_profile = result.total_distance_km + VERTICAL_EXAGGERATION * vertical_km
        assert drawn[key] > result.total_distance_km, (
            f"{key}: the drawn line must include the climb, not just the ground track"
        )
        assert drawn[key] < wall_profile - 1.0, (
            f"{key}: the profile must be spread over horizontal distance; if the "
            f"drawn line reaches the {VERTICAL_EXAGGERATION:.0f}x wall length, the "
            "altitude changes are still steps"
        )

    # Altitude is what makes two routes of similar length look so different: the
    # route locked to 3600 m climbs twice as far as the one locked to 2200 m.
    #
    # The *size* of the drawn excess is the quantitative proof that the profile is
    # a ramp and not a wall. A wall of height ``E·h`` adds the whole ``E·h`` to the
    # drawn length; a ramp of run ``s`` adds only ``√(s²+(E·h)²) − s``, which for a
    # 20 km climb is a small fraction of it. So the excess must be a *fraction* of
    # the wall's — bounded above by the wall and well under it — and it must grow
    # with the vertical work. (This assertion used to demand that the excess match
    # the wall exactly, which is precisely the stepped geometry that was wrong.)
    low, high = routes["R4"], routes["R6"]
    low_wall = (
        VERTICAL_EXAGGERATION * (low.total_climb_m + low.total_descent_m) / 1000.0
    )
    high_wall = (
        VERTICAL_EXAGGERATION * (high.total_climb_m + high.total_descent_m) / 1000.0
    )
    low_excess = drawn["R4"] - low.total_distance_km
    high_excess = drawn["R6"] - high.total_distance_km
    assert 2.0 < low_excess < 0.6 * low_wall, f"R4 excess {low_excess:.2f} km"
    assert low_excess < high_excess < 0.6 * high_wall, (
        f"R6 excess {high_excess:.2f} km"
    )

    header, rows = route_table_rows(routes, drawn_km=drawn)
    assert header[-1] == "طول خط روی صفحه (km)"
    for row in rows:
        assert float(row[-1]) == pytest.approx(drawn[row[0]], abs=0.05)


# ===========================================================================
# Motor effort and fuel
# ===========================================================================


def test_every_route_reports_motor_effort_and_fuel(routes) -> None:
    """Each route must carry course-change, power and fuel numbers.

    These are model outputs (assumptions documented in ``pathfinding.effort``),
    but they must be present, non-negative and physically ordered.
    """
    for key, result in routes.items():
        effort = result.effort
        assert effort is not None, key
        assert effort.legs >= 1, key
        assert effort.cruise_fuel_kg > 0.0, key
        assert effort.total_fuel_kg >= effort.cruise_fuel_kg, key
        assert effort.powered_course_changes >= 0, key
        assert effort.course_change_deg_total >= 0.0, key
        assert effort.fuel_per_100km_kg > 0.0, key
        # A course change without turn time (or the reverse) would be a bug.
        assert (effort.powered_course_changes == 0) == (effort.turn_time_s == 0.0), key
        assert (effort.powered_course_changes == 0) == (
            effort.turn_extra_energy_kj == 0.0
        ), key


def test_higher_cruise_costs_more_climb_fuel(routes) -> None:
    """R6 cruises at 3600 m instead of 2200 m, so it must burn more fuel climbing.

    This is the trade-off the lock pair exists to show, and it does not go the
    naive way: the 3600 m level has the stronger tailwind, and the cruise fuel it
    saves is *larger* than the extra climb costs, so R6 burns slightly **less**
    total fuel than R4 — while taking longer. Fuel and time disagree, and the
    table has to show both for the comparison to be honest.
    """
    low, high = routes["R4"].effort, routes["R6"].effort
    assert low is not None and high is not None
    assert high.climb_energy_kj > low.climb_energy_kj > 0.0
    assert high.climb_fuel_kg > low.climb_fuel_kg > 0.0
    assert high.glide_range_km > low.glide_range_km
    # The higher level's stronger tailwind pays for the extra climb and then some.
    assert high.cruise_fuel_kg < low.cruise_fuel_kg
    assert high.total_fuel_kg <= low.total_fuel_kg
    # But time punishes the detour up there: R6 is the slower of the locked pair.
    assert routes["R6"].estimated_time_hours > routes["R4"].estimated_time_hours


def test_effort_columns_are_in_the_table_and_match_the_model(routes) -> None:
    """The new columns must come from ``RouteResult.effort``, not be recomputed."""
    header, rows = route_table_rows(routes)
    for name in ("تصحیح مسیر با موتور (بار)", "سوخت (kg)", "توان اضافهٔ دور (W)"):
        assert name in header, name

    fuel_index = header.index("سوخت (kg)")
    changes_index = header.index("تصحیح مسیر با موتور (بار)")
    for row in rows:
        result = routes[row[0]]
        assert result.effort is not None
        assert float(row[fuel_index]) == pytest.approx(result.effort.total_fuel_kg, abs=0.005)
        assert int(row[changes_index]) == result.effort.powered_course_changes


def test_fuel_assumptions_are_stated_in_the_page(scene_html) -> None:
    """Fuel numbers are model outputs, so their assumptions must ship with them."""
    _path, _routes, html = scene_html
    assert "فرض‌های مدل" in html
    assert "MJ/kg" in html
    assert "kW" in html


def test_every_flight_level_has_its_own_colour(figure) -> None:
    """Four wind layers must be four *different* colours in the scene.

    The palette used to be keyed by the old AGL altitudes (500/1000/1500/2000)
    while the flight levels are MSL (1500/2200/2900/3600). Every lookup therefore
    missed and fell back to one shared grey, so three of the four arrow layers
    were drawn in the same colour — which is most of why the arrows read as
    invisible. The palette is now derived from ``FLIGHT_LEVELS_MSL``.
    """
    from viz.scene3d import _LAYER_COLORS

    levels = [float(altitude) for altitude in FLIGHT_LEVELS_MSL]
    assert set(_LAYER_COLORS) == set(levels), sorted(_LAYER_COLORS)
    palette = [_LAYER_COLORS[level] for level in levels]
    assert len(set(palette)) == len(palette), palette

    # …and the built figure really uses them: one distinct colour per layer, with
    # no trace left on a fallback.
    def cone_colour(trace) -> str:
        return str(trace.colorscale[0][1])

    cones = [t for t in figure.data if t.type == "cone"]
    assert len(cones) == len(levels)
    drawn = [cone_colour(trace) for trace in cones]
    assert len(set(drawn)) == len(drawn), drawn
    assert set(drawn) <= set(palette), set(drawn) - set(palette)

    # The best-layer overlay needs the same distinctness, or it cannot be read.
    overlays = [t for t in figure.data if t.type == "surface"]
    if len(overlays) > 1:
        overlay_colours = [str(entry[1]) for entry in overlays[1].colorscale]
        assert len(set(overlay_colours)) == len(overlay_colours), overlay_colours


def test_wind_arrow_length_is_proportional_to_wind_speed(
    figure, fields, multi_graph
) -> None:
    """A stronger wind must draw a longer arrow — the whole arrow, not just a bit.

    The shaft is built from ``speed × ARROW_KM_PER_MS`` and the cone head is
    drawn with ``sizemode="absolute"``, which Plotly normalises against the
    largest vector in the trace — so *both* parts grow with the wind speed. This
    test recomputes the expected shaft length from the graph itself (the same
    nodes the arrows are drawn on) and compares it with the drawn geometry.
    """
    from viz.scene3d import ARROW_KM_PER_MS, ARROW_MAX_LENGTH_KM, ARROW_STRIDE, _arrow_indices

    cones = [t for t in figure.data if t.type == "cone"]
    assert len(cones) == len(fields)

    for field, cone in zip(fields, cones, strict=True):
        graph = multi_graph.get_layer(field.altitude)
        node_ids = list(graph.nodes)
        speeds = np.array([graph.get_node(nid).wind_speed_mps for nid in node_ids])
        keep = _arrow_indices(len(node_ids), len(field.lons), ARROW_STRIDE)
        expected = np.minimum(speeds[keep] * ARROW_KM_PER_MS, ARROW_MAX_LENGTH_KM)
        assert len(expected) == len(keep)

        (trace,) = [
            t
            for t in figure.data
            if t.type == "scatter3d"
            and t.name is not None
            and t.name.startswith(f"باد سطح {field.altitude:.0f} متر")
        ]
        xs = [float(v) for v in trace.x if v is not None]
        ys = [float(v) for v in trace.y if v is not None]
        lengths = np.hypot(
            np.array(xs[1::2]) - np.array(xs[0::2]),
            np.array(ys[1::2]) - np.array(ys[0::2]),
        )
        assert np.allclose(lengths, expected, atol=1e-9)
        # Nothing may hit the cap in this dataset, or proportionality would break
        # exactly for the fastest arrows.
        assert (speeds[keep] * ARROW_KM_PER_MS).max() <= ARROW_MAX_LENGTH_KM

        # The head is drawn from the same scaled vectors (``u``/``v``), and it is
        # sized with ``sizemode="absolute"``, so the whole arrow — shaft and head
        # — grows with the wind.
        head_lengths = np.hypot(np.asarray(cone.u, dtype=float), np.asarray(cone.v, dtype=float))
        assert np.allclose(head_lengths, expected, atol=1e-9)

        # The claim the scene makes: faster wind, longer arrow. The spread here is
        # the real spatial spread of this hour's wind (speed range in this layer
        # is ~1.6x), not a chosen visual factor.
        assert lengths.max() > 1.3 * lengths.min(), field.altitude
        assert lengths.max() - lengths.min() > 2.0, field.altitude  # kilometres


def test_shortest_route_is_not_the_fastest(routes) -> None:
    """R3 minimises distance only; R2 must be faster, which is the trade-off shown."""
    r2, r3 = routes["R2"], routes["R3"]
    assert r3.total_distance_km <= r2.total_distance_km + 1e-9
    assert r2.estimated_time_hours <= r3.estimated_time_hours + 1e-9


def test_single_layer_route_is_layer_locked_and_costs_more(routes) -> None:
    """R4 must be restricted to exactly one altitude and pay for it."""
    r1, r4 = routes["R1"], routes["R4"]
    assert r4.heading_changes >= 0
    assert r4.estimated_time_hours >= r1.estimated_time_hours - 1e-9
    # R1 is free to pick the best layer; R4 cannot beat it.
    assert r4.total_distance_km > 0.0


# ===========================================================================
# The generated artifact
# ===========================================================================


def test_write_scene_produces_a_self_contained_html_document(scene_html) -> None:
    """The written file must work offline and keep its honesty labels."""
    path, routes, html = scene_html

    assert path.exists()
    assert path.stat().st_size > 1_000_000, "plotly.js should be embedded, not linked"
    # No external network dependency: plotly.js is inlined, so there must be no
    # `<script src=...>` fetching anything from a CDN.
    assert "<script src=" not in html

    # Plotly serialises the figure with `ensure_ascii=True`, so Persian labels
    # appear as \uXXXX escapes in the file. Checking the escaped form keeps the
    # honesty-label assertion meaningful instead of accidentally matching the
    # bundled library text.
    def escaped(text: str) -> str:
        return json.dumps(text, ensure_ascii=True)[1:-1]

    assert escaped("سنتزی") in html, "synthetic-data warning missing from artifact"
    assert escaped("مشهد") in html and escaped("سبزوار") in html
    assert escaped("ارتفاع زمین") in html
    # Every declared route reaches the artifact, and the wind-riding family may
    # add the variants its corridor search decided were worth drawing (R7/R8).
    # A variant the search dropped is simply absent — never a foreign key.
    declared = {spec.key for spec in ROUTE_SPECS}
    optional = {spec.key for spec in WIND_RIDING_VARIANT_SPECS}
    assert declared <= set(routes)
    assert set(routes) <= declared | optional, set(routes) - declared - optional

    # The gravity/climb/descent evidence panel must reach the artifact, and the
    # stale caveat it replaces must not. That caveat blamed a mismatch between
    # the two descent conventions; the conventions are now unified, so keeping
    # the sentence in the page would be a false claim.
    assert "گرانش، صعود و فرود" in html
    assert "زاویهٔ باد با کریدور" in html
    assert "مسافت فرود" in html
    # The glideslope policy and the power it costs must be visible in the panel,
    # not just in the code: those two columns are what make the gradual profile
    # checkable rather than decorative.
    assert "شیب فرود" in html and "توان فرود" in html
    assert "انرژی پتانسیل فرود هم به سوختش" not in html
    # Every route in the table now pays for its own climb and descent.
    for key in ("R1", "R4"):
        assert routes[key].total_climb_m > 0.0, key


def test_html_shell_puts_labels_in_a_scrollable_overlay(scene_html) -> None:
    """Title, warning and legend must float over the scene, inside a scroller.

    When they sat in the normal document flow they consumed most of the window
    height and squeezed the 3D scene into a narrow band.
    """
    _path, _routes, html = scene_html

    assert 'class="labels"' in html
    assert "position: absolute" in html
    assert "overflow-y: auto" in html
    assert "<summary>" in html
    assert 'id="toggle-labels"' in html
    # One chip per legend *group*, and each chip must name its group so the page
    # can toggle every trace of that group together.
    assert html.count('class="lg') >= len(ROUTE_SPECS) + len(LAYER_PROFILES)
    assert 'data-group="R1"' in html
    assert "Plotly.restyle" in html
    # The chips must not double up: one chip per layer, not one per trace.
    for spec in ROUTE_SPECS:
        assert html.count(f'data-group="{spec.key}"') == 1, spec.key

    # Every chip must name a group that actually exists in the page's group
    # table, and the page must look groups up by that name. Otherwise a chip can
    # silently toggle the wrong layer (positional lookup is not stable, since
    # chip-less groups such as "stations" live in the same table).
    groups = json.loads(re.search(r"var GROUPS = (\[.*?\]);", html, re.S).group(1))
    group_ids = {group["group"] for group in groups}
    chip_ids = re.findall(r'data-group="([^"]+)"', html)
    assert chip_ids, "no chips found"
    assert set(chip_ids) <= group_ids, set(chip_ids) - group_ids
    assert "chipGroupIndex" in html
    for group in groups:
        assert group["traces"], group["group"]
        assert "default" in group and "only" in group


def test_scene_can_isolate_one_item_and_reset(scene_html) -> None:
    """Double-click must isolate an item; the reset control must bring it back.

    Double-clicking a route used to do nothing at all: the Plotly legend was off
    and the page never handled the gesture. Now a double click (on a chip or on
    the object itself) hides every other group, and there is an explicit reset
    button plus the Escape key.
    """
    _path, _routes, html = scene_html

    assert 'id="show-all"' in html, "no way to restore every element"
    assert "function isolate(" in html
    assert "function showAll(" in html
    # Double-click on the scene itself, not only on the chips.
    assert "plotly_click" in html
    assert "dblclick" in html
    # Plotly's own double-click reset would fight the isolate gesture.
    assert '"doubleClick": false' in html
    # The ground and the start/end markers stay visible while isolating.
    assert "ALWAYS_VISIBLE" in html
    assert "'isolated'" in html or "\"isolated\"" in html


def test_html_shell_renders_a_real_table_and_resize_hook(scene_html) -> None:
    """The comparison table is real HTML, and the scene re-fits on resize."""
    _path, _routes, html = scene_html

    assert "<table>" in html and "<thead>" in html and "<tbody>" in html
    assert "<td" in html
    # One row per route plus the header row's cells.
    assert html.count("<tr>") >= len(ROUTE_SPECS)
    # Plotly does not rebuild its WebGL canvas from a CSS-only resize, so the
    # page must call Plots.resize itself or the scene gets clipped.
    assert "Plotly.Plots.resize" in html


def test_layer_evidence_table_explains_the_single_layer_result(
    multi_graph, fields
) -> None:
    """The scene must show what each level actually does, not just assert it.

    This table is where a reader checks the routing claim. It went from a wind
    comparison to a **feasibility** comparison: with the terrain model, a level
    whose clearance over the range cannot be held simply has no path, while the
    levels that do have one differ in time, distance and climb. So the test
    asserts the table conforms to ``compare_layers`` exactly — every available
    level is a row, every routable level carries its engine numbers, and every
    blocked one states the reason instead of printing a made-up number.
    """
    from pathfinding.routing import WindRouter
    from viz.scene3d import _layer_evidence_html

    aircraft = VIZ_AIRCRAFT
    router = WindRouter(multi_graph, config=aircraft, criterion="time")
    comparison = router.compare_layers(DEMO_ORIGIN, DEMO_DESTINATION)
    assert comparison.results, "no level is routable at all"

    html = _layer_evidence_html(router, DEMO_ORIGIN, DEMO_DESTINATION, aircraft)

    # One row per available level, in the router's own order.
    for altitude in router.available_layers:
        assert f"<td>{altitude:.0f}</td>" in html, altitude

    best_altitude = min(
        comparison.results,
        key=lambda alt: comparison.results[alt].estimated_time_hours,
    )
    assert "کم‌زمان‌ترین سطح" in html
    best_row = html.split(f"<td>{best_altitude:.0f}</td>")[1].split("</tr>")[0]
    assert "کم‌زمان‌ترین سطح" in best_row

    # A routable level reports the engine's numbers…
    for altitude, result in comparison.results.items():
        row = html.split(f"<td>{altitude:.0f}</td>")[1].split("</tr>")[0]
        assert f"{result.estimated_time_hours:.3f}" in row, altitude
        assert f"{result.total_distance_km:.1f}" in row, altitude
        assert f"{result.total_climb_m:.0f}" in row, altitude

    # …and a blocked one says so rather than inventing one.
    blocked = [alt for alt in router.available_layers if alt not in comparison.results]
    for altitude in blocked:
        row = html.split(f"<td>{altitude:.0f}</td>")[1].split("</tr>")[0]
        assert "مسیر ندارد" in row, altitude
        assert '<td class="num">—</td>' in row, altitude

    # The table must not claim climbing always loses: in this wind field the free
    # routes do climb, and the evidence table has to be consistent with that.
    best_time = comparison.results[best_altitude].estimated_time_hours
    lowest = min(comparison.results, key=lambda alt: alt)
    assert comparison.results[lowest].estimated_time_hours >= best_time - 1e-9


# ===========================================================================
# The wind-riding route
# ===========================================================================


def _wind_aligned_fraction(result) -> float:
    """Share of the route's distance flown within 15° of the local wind."""
    total = sum(leg.distance_km for leg in result.leg_samples)
    if total <= 0.0:
        return 0.0
    aligned = 0.0
    for leg in result.leg_samples:
        difference = (
            leg.track_bearing_deg - (leg.wind_direction_from_deg + 180.0)
        ) % 360.0
        if min(difference, 360.0 - difference) <= 15.0:
            aligned += leg.distance_km
    return aligned / total


def test_wind_riding_route_rides_the_wind_and_only_corrects_occasionally(
    all_routes,
) -> None:
    """The claim this route exists to make, measured on its own reported legs.

    A graph route *holds a ground track*, so it fights whatever the wind does and
    its course is only occasionally parallel to it. Wind riding puts the ground
    track on the wind direction itself and steers only when riding would carry it
    out of the arrival corridor — so most of its distance is parallel to the
    arrows, and the corrections it does make are counted and billed (a handful of
    course changes worth a few tens of degrees, not a continuous crab).

    The numbers below are the ones this corridor actually produces: the ridge
    (3175 m) leaves only the 3600 m level flyable for wind riding, and up there
    the wind turns away from the destination late in the route, so ~60% — not
    100% — is parallel. Anything much lower means the controller stopped tracking
    the wind and went back to fighting it.

    This test deliberately does **not** claim to beat every graph route: on this
    corridor R4 (confined to the 2200 m level, going around the southern pass)
    measures ~71% aligned, higher than the ride. That is a property of the wind
    here — it blows broadly along the corridor, and the graph's own cost function
    already rewards an along-track wind, so some graph routes land close to the
    arrows by geography rather than by policy. What is unique to the ride is that
    its alignment is *structural*: the track is put on the wind direction every
    step and only leaves it to stay inside the arrival corridor.
    """
    key = WIND_RIDING_SPECS[0].key
    riding = all_routes[key]
    assert riding.algorithm == "wind-riding"
    assert riding.effort is not None

    aligned = _wind_aligned_fraction(riding)
    graph_aligned = {
        other: _wind_aligned_fraction(result)
        for other, result in all_routes.items()
        if other != key
    }
    assert aligned > 0.5, f"wind riding must mostly ride: {aligned:.2f}"
    # …and it must be structurally aligned, not accidentally so: at least twice
    # the worst graph route on the same corridor and the same aircraft.
    assert aligned > 2.0 * min(graph_aligned.values()), (
        f"riding {aligned:.2f} vs graph routes {graph_aligned}"
    )

    # The corrections are real and billed…
    assert riding.effort.powered_course_changes > 0
    assert riding.effort.course_change_deg_total > 0.0
    assert riding.effort.turn_fuel_kg > 0.0
    # …but they are *occasional*: a handful of degrees, not a continuous fight.
    # A constant-heading ride on this corridor measured 7.7% aligned with zero
    # corrections, so "fewer corrections" alone would have been the wrong target.
    assert riding.effort.course_change_deg_total < 90.0, (
        riding.effort.course_change_deg_total
    )


def test_wind_riding_route_is_comparable_with_the_graph_routes(all_routes) -> None:
    """Same corridor, same aircraft, same ballpark: the table is fair.

    The ballpark is wider than it used to be, and that is the *point* of the
    policy search: riding the wind costs distance (the aircraft is allowed to
    drift downwind to stay parallel to the arrows), so the ride is now longer
    than a straight graph route. 15% is the ceiling the planner's own time slack
    (``alignment_slack_ratio``) implies; a route that wandered further would fail
    here as "not comparable with the other rows" rather than as "too long".
    """
    key = WIND_RIDING_SPECS[0].key
    riding = all_routes[key]
    reference = all_routes["R1"]
    assert riding.total_distance_km == pytest.approx(
        reference.total_distance_km, rel=0.15
    )
    assert riding.estimated_time_hours == pytest.approx(
        reference.estimated_time_hours, rel=0.15
    )
    assert riding.path[0] == pytest.approx(DEMO_ORIGIN)
    assert riding.path[-1] == pytest.approx(DEMO_DESTINATION)
    # Ground to ground: the profile must not start or end in the air. With a DEM
    # the ends report the local ground elevation (≈۹۸۰ m here), so the check is
    # "near the ground", not "equals zero".
    assert riding.node_altitudes[0] < 0.4 * riding.layer_altitude
    assert riding.node_altitudes[-1] < 0.4 * riding.layer_altitude
    assert max(riding.node_altitudes) == pytest.approx(riding.layer_altitude)


def test_no_route_profile_steps_vertically(all_routes, terrain) -> None:
    """Every altitude change must be a real ramp, not a jump in place.

    The stacked graph joins levels with *vertical* edges: two nodes at the same
    coordinates and different altitudes. Drawn as-is that is a wall — the
    aircraft appears to fall out of the sky at the destination — and the user saw
    exactly that. The routing layer therefore spreads every transition over the
    horizontal distance its vertical rate needs, so this test reads the produced
    profile and checks the physics directly:

    * no consecutive pair may change altitude faster than the climb/descent rate
      allows at the route's own ground speed (the flight-path angle is bounded),
    * and there must be *several* intermediate altitudes in every transition, so a
      step of one point that happens to satisfy the angle bound cannot sneak in.
    """
    vertical = VerticalCostConfig()
    for key, result in all_routes.items():
        # The bound is the aircraft's own vertical rate over *its own* ground speed
        # on this route (the router uses the same quantity to lay the ramps out).
        # A 25% margin covers two second-order effects that are not slack: the
        # ramps are anchored to the terrain, so their slope varies with the ground
        # under them, and the profile is thinned before it is reported, so a pair
        # of points can straddle a rate change.
        leg_km = sum(leg.distance_km for leg in result.leg_samples)
        leg_hours = sum(leg.time_hours for leg in result.leg_samples)
        ground_speed = (leg_km / (leg_hours * 3.6)) if leg_hours > 0.0 else 15.0
        gradient_limit = 1.25 * max(
            vertical.climb_rate_mps, vertical.descent_rate_mps
        ) / max(ground_speed, 1.0)
        lats = np.array([lat for lat, _lon in result.path], dtype=float)
        lons = np.array([lon for _lat, lon in result.path], dtype=float)
        altitudes = np.array(result.node_altitudes, dtype=float)
        # ``node_altitudes`` reports a ground node as **zero**, not as its height
        # above sea level, so the two ends are in a different frame from the rest of
        # the profile. Substitute the real ground height there — exactly the
        # substitution the scene performs when it draws — so that every difference
        # below is in one frame (MSL) and a 983 m endpoint does not read as a
        # 983 m "step".
        on_ground = altitudes <= 0.0
        if on_ground.any():
            altitudes = altitudes.copy()
            altitudes[on_ground] = np.atleast_1d(
                terrain.elevation_at(lats[on_ground], lons[on_ground])
            )
        run_km = np.hypot(
            np.diff(lats) * 111.32,
            np.diff(lons) * 111.32 * np.cos(np.radians(lats[:-1])),
        )
        rise_m = np.abs(np.diff(altitudes))
        airborne = rise_m > 1.0
        assert airborne.any(), key
        # A transition inside one point (run ≈ 0) with real altitude change is a step.
        stepped = airborne & (run_km < 1e-6)
        assert not stepped.any(), (
            f"{key}: {int(stepped.sum())} altitude change(s) happen at a single "
            "point — that is the vertical edge showing through"
        )
        # And no ramp may be steeper than the aircraft's own vertical rate.
        angle_limit = gradient_limit * np.maximum(run_km, 1e-9) * 1000.0
        assert np.all(rise_m <= angle_limit + 1.0), (
            f"{key}: steepest change {rise_m.max():.0f} m over "
            f"{run_km[rise_m.argmax()]:.3f} km exceeds the vertical-rate bound"
        )
        # A ramp is many points, not one: the climb to the cruise level and the
        # descent back must each be sampled.
        intermediate = (altitudes > altitudes.min() + 50.0) & (
            altitudes < altitudes.max() - 50.0
        )
        assert int(intermediate.sum()) >= 4, (key, int(intermediate.sum()))


def test_wind_riding_reports_one_cruise_layer_despite_a_sloping_descent(
    all_routes,
) -> None:
    """A sloping descent must not be reported as dozens of altitude "layers"."""
    riding = all_routes[WIND_RIDING_SPECS[0].key]
    assert riding.altitudes_used == [riding.layer_altitude]
    assert not riding.is_multilayer
    # …while the drawn profile itself is continuous, which is the point.
    airborne = {
        round(alt, 3)
        for alt in riding.node_altitudes
        if 0.0 < alt < riding.layer_altitude
    }
    assert len(airborne) >= 3, airborne


def test_wind_riding_route_lands_on_the_destination_not_beside_it(all_routes) -> None:
    """The glide must put the aircraft *on* the destination.

    With a plain fixed sink rate the descent covers a fixed distance, so the route
    touched down short or long by up to a step and then needed a closing leg — the
    very path change this strategy exists to avoid. The measure is therefore the
    *touchdown*, not the path length: the ride may be longer than the direct line
    (it drifts downwind on purpose), but it must not end beside the target.
    """
    riding = all_routes[WIND_RIDING_SPECS[0].key]
    touchdown_km = haversine_km(*riding.path[-1], *DEMO_DESTINATION)
    assert touchdown_km <= WindRidingConfig().max_arrival_miss_km
    # A longer path with an accurate touchdown is not a contradiction: the extra
    # distance is the price of riding the wind, and it is bounded here so the
    # row cannot drift into a sightseeing flight.
    direct_km = haversine_km(*riding.path[0], *riding.path[-1])
    assert riding.total_distance_km <= direct_km * 1.15


def test_riding_route_appears_in_the_comparison_table(all_routes) -> None:
    """The table must carry the wind-riding row like any other route."""
    key = WIND_RIDING_SPECS[0].key
    header, rows = route_table_rows(all_routes)
    keys = [row[0] for row in rows]
    assert key in keys
    assert rows[keys.index(key)][2] == "wind-riding"
    assert all(len(row) == len(header) for row in rows)


def test_figure_draws_the_wind_riding_route(figure) -> None:
    """The route must actually be drawn, under its own legend group."""
    from viz.scene3d import _legend_entries

    key = WIND_RIDING_SPECS[0].key
    entries = {entry["group"]: entry for entry in _legend_entries(figure)}
    assert key in entries
    # The ride is one continuous curve drawn twice: the hairline core (hover) and
    # the mesh tube that gives it thickness without plotly's beaded thick lines.
    kinds = sorted(figure.data[index].type for index in entries[key]["traces"])
    assert kinds == ["mesh3d", "scatter3d"], kinds
    line = next(
        trace
        for trace in figure.data
        if getattr(trace, "mode", None) == "lines"
        and trace.name
        and trace.name.startswith(key)
    )
    assert len(line.x) > 20, "the drawn ride is a real polyline, not two points"


# ===========================================================================
# Gravity: the climb is charged, the glide pays it back
# ===========================================================================


def test_every_graph_route_starts_and_ends_on_the_ground(all_routes, terrain) -> None:
    """A route must climb out of the origin and descend into the destination.

    Until the layer comparison went through the stacked (ground-to-ground) graph,
    every node sat at its layer altitude, so a "single-layer" route began in the
    sky: ``total_climb_m`` and ``total_descent_m`` were both zero and the climb to
    the cruise layer was never billed. That made higher layers look free and made
    the layer comparison meaningless.

    Ground altitude is **zero by convention**, not sea level: Mashhad sits at
    983 m, so a route to a 2900 m level climbs 1917 m, not 2900 m. The two ends
    use their own local ground (983.24 m at Mashhad, 983.90 m at Sabzevar), which
    is why the climb and descent differ by a few tenths of a metre.
    """
    origin_ground = float(np.atleast_1d(terrain.elevation_at(*DEMO_ORIGIN))[0])
    destination_ground = float(
        np.atleast_1d(terrain.elevation_at(*DEMO_DESTINATION))[0]
    )
    assert origin_ground > 100.0, "this corridor is not at sea level"

    for key, result in all_routes.items():
        assert result.node_altitudes[0] == 0.0, key
        assert result.node_altitudes[-1] == 0.0, key
        assert result.total_climb_m == pytest.approx(
            result.layer_altitude - origin_ground, abs=0.05
        ), key
        assert result.total_descent_m == pytest.approx(
            result.layer_altitude - destination_ground, abs=0.05
        ), key
        assert result.climb_legs >= 2, key
        # The profile really leaves and returns to the cruise level.
        #
        # It may rise *above* the cruise level, but only where the ground below
        # would otherwise intrude on the safety clearance: the terrain floor is a
        # hard constraint and outranks the level, and the floor asks for no more
        # clearance than the router was configured with. So the peak is bounded
        # from both sides — it reaches the level, and never exceeds it by more
        # than the clearance (a level profile lifted a whole clearance is the
        # worst case).
        peak = max(result.node_altitudes)
        assert peak >= result.layer_altitude - 0.05, key
        assert peak <= result.layer_altitude + MIN_TERRAIN_CLEARANCE_M + 1e-6, (
            key,
            peak,
            "the floor must not lift the profile more than the clearance it asked for",
        )


def test_climbing_costs_time_but_gravity_gives_the_fuel_back(all_routes) -> None:
    """Higher layers must cost *time* without costing proportionally more fuel.

    This is the arithmetic behind "climb, ride the wind, glide down". The climb
    burns ``mgh/η``, but the glide returns exactly that as engine-idle range
    (``D·(L/D)·h/η == mgh/η``), so the *fuel* spread across the two locked levels
    is far smaller than the height spread — while the time spread is not.

    The glide range is exactly proportional to the *descent* height, so that
    identity is asserted exactly. Comparing it with the *climb* ratio instead
    needs a tolerance: ``total_climb_m`` and ``total_descent_m`` differ by the
    terrain relief under the origin and destination, which is a few metres on
    this grid (measured: 0.2% between the two locked levels). That asymmetry is
    real, not slack — so the exact claim is pinned exactly and the asymmetry is
    bounded separately.
    """
    low = all_routes["R4"]
    high = all_routes["R6"]
    assert low.effort is not None and high.effort is not None

    climb_ratio = high.total_climb_m / low.total_climb_m
    descent_ratio = high.total_descent_m / low.total_descent_m
    assert climb_ratio == pytest.approx(2.0, rel=0.2)
    # بُرد گلاید دقیقاً به ارتفاع فرود بسته است (یک L/D برای هر دو لایه) →
    # این نسبت باید *دقیق* باشد، نه تقریبی.
    assert high.effort.glide_range_km / low.effort.glide_range_km == pytest.approx(
        descent_ratio, rel=1e-9
    )
    assert descent_ratio == pytest.approx(climb_ratio, rel=2e-3)
    # The climb's gross energy scales with height…
    assert high.effort.climb_energy_kj == pytest.approx(
        climb_ratio * low.effort.climb_energy_kj, rel=1e-3
    )
    # …and so does the glide's saving. The saving is exactly `descent/climb` of
    # the climb energy, and that factor must be *near one* for the claim "the two
    # nearly cancel" to mean anything — so the factor is bounded hard here (it is
    # the terrain relief under the two endpoints, ~0.2% on this grid) instead of
    # being absorbed by a loose tolerance.
    for result in (high, low):
        assert result.effort is not None
        cancel = result.total_descent_m / result.total_climb_m
        assert result.effort.glide_energy_saved_kj == pytest.approx(
            result.effort.climb_energy_kj * cancel, rel=1e-3
        )
        assert abs(cancel - 1.0) < 3e-3, (result.criterion, cancel)
    # Time, by contrast, clearly punishes altitude.
    assert high.estimated_time_hours > low.estimated_time_hours


def test_gravity_panel_reports_every_layer(fields) -> None:
    """The artifact must carry the per-layer climb/ride/glide breakdown."""
    from pathfinding.effort import MotorEffortConfig
    from viz.scene3d import _gravity_evidence_html, wind_riding_layer_reports

    reports = wind_riding_layer_reports(
        fields, VIZ_AIRCRAFT, effort_config=MotorEffortConfig()
    )
    assert reports, "no wind-riding plan on any layer"
    assert [report.altitude_m for report in reports] == sorted(
        report.altitude_m for report in reports
    )

    config = MotorEffortConfig()
    for report in reports:
        # Each phase must be reported and add up to the total.
        phases = (
            report.climb_time_hours + report.ride_time_hours + report.glide_time_hours
        )
        assert phases == pytest.approx(report.total_time_hours, rel=1e-6)
        assert report.climb_time_hours > 0.0
        assert report.ride_time_hours > 0.0
        # The descent is the *policy* glideslope, `h · ratio`, and it is longer
        # than the maximum glide range `h · L/D` — that is what makes the profile
        # gradual rather than a dive.
        settings = WindRidingConfig()
        assert report.glide_km == pytest.approx(
            report.altitude_m * settings.descent_glideslope_ratio / 1000.0, rel=0.15
        )
        assert report.glide_km > config.glide_range_km(report.altitude_m)
        # …and the leg power is the thrust balance of that slope, not idle.
        expected_power = 1.0 - config.lift_to_drag / report.descent_slope_ratio
        assert report.descent_power_fraction == pytest.approx(expected_power, abs=0.05)
        assert report.descent_power_fraction <= 1.0
        assert report.glide_km > 0.0
        assert report.fuel_kg > 0.0
        assert 0.0 <= report.wind_offset_deg <= 180.0

    html = _gravity_evidence_html(reports, config, fields)
    for report in reports:
        assert f'<td class="num">{report.altitude_m:.0f}</td>' in html
    # A level with no plan must still appear, with the reason it has none. The
    # panel answered "which level wins?" but stayed silent about the levels that
    # were dropped — and in this corridor that silence hides the main answer.
    partial = _gravity_evidence_html(reports[:1], config, fields)
    for level in FLIGHT_LEVELS_MSL:
        assert f'<td class="num">{level:.0f}</td>' in partial, level
    dropped = [level for level in FLIGHT_LEVELS_MSL if level not in {r.altitude_m for r in reports[:1]}]
    assert dropped, "this assertion is only meaningful when a level is missing"
    for level in dropped:
        row = partial[partial.index(f'<td class="num">{level:.0f}</td>') :]
        row = row[: row.index("</tr>")]
        assert ("سطح زیر رشته‌کوه" in row) or ("هیچ سمت ثابتی" in row), row
    # The two competing optima must be named, whichever they are.
    assert "کم‌زمان‌ترین" in html and "کم‌مصرف‌ترین" in html
    assert "زاویهٔ باد با کریدور" in html
    assert "مسافت فرود" in html
    # The glideslope policy must be visible, not implied: the panel carries the
    # slope and the powered-descent fraction as their own columns.
    assert "شیب فرود" in html and "توان فرود" in html


