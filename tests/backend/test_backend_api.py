"""تست‌های HTTP: endpointها، اعتبارسنجی، خطاها، jobهای async و داده واقعی."""

import time

import pytest
from conftest import pt

from backend import ApiApp, WindDataProvider
from backend.app import DEFERRED_OPERATIONS, IMPLEMENTED_OPERATIONS

BASE = {"origin": pt(57.0), "destination": pt(60.0)}


def test_health_of_static_endpoints(call):
    assert call("GET", "/v1/algorithms")[0] == 200
    status, body, _ = call("GET", "/v1/wind-layers")
    assert status == 200 and [layer["altitude_m"] for layer in body] == [500, 1000, 1500, 2000]
    assert body[0]["last_updated"] == "2026-01-01T00:00:00+00:00"


def test_route_sync_returns_standard_result(call):
    status, body, headers = call("POST", "/v1/routes", BASE)
    assert status == 200 and headers["X-Request-Id"]
    assert body["path"][0] == pt(57.0) and body["path"][-1] == pt(60.0)
    assert body["total_distance_km"] > 0 and body["estimated_time_hours"] > 0
    assert body["layer_altitude_m"] in (500, 1000, 1500, 2000)
    assert body["algorithm"] == "a_star" and body["is_saved"] is False
    assert call("GET", f"/v1/routes/{body['route_id']}")[1] == body


@pytest.mark.parametrize("algo", ["a_star", "dijkstra"])
def test_both_algorithms_same_optimal_cost(call, algo):
    a = call("POST", "/v1/routes", {**BASE, "algorithm": "a_star"})[1]
    b = call("POST", "/v1/routes", {**BASE, "algorithm": algo})[1]
    assert b["algorithm"] == algo
    assert b["total_cost"] == pytest.approx(a["total_cost"], rel=1e-6)


def test_delete_route(call):
    rid = call("POST", "/v1/routes", BASE)[1]["route_id"]
    assert call("DELETE", f"/v1/routes/{rid}")[0] == 204
    assert call("GET", f"/v1/routes/{rid}")[0] == 404
    assert call("DELETE", f"/v1/routes/{rid}")[0] == 404


def test_compare_layers_marks_single_best(call):
    rid = call("POST", "/v1/routes", BASE)[1]["route_id"]
    status, body, _ = call("GET", f"/v1/routes/jobs/{rid}/compare-layers")
    assert status == 200 and len(body["rows"]) == 4
    assert sum(r["is_best"] for r in body["rows"]) == 1
    best = next(r for r in body["rows"] if r["is_best"])
    assert best["total_cost"] == min(r["total_cost"] for r in body["rows"])


def test_manual_layer_and_altitude_range(call):
    _, body, _ = call("POST", "/v1/routes", {**BASE, "layer_mode": "manual", "altitude_m": 1500})
    assert body["layer_altitude_m"] == 1500
    _, body, _ = call(
        "POST", "/v1/routes", {**BASE, "constraints": {"altitude_range_m": [1500, 2000]}}
    )
    assert body["layer_altitude_m"] in (1500, 2000)
    status, err, _ = call(
        "POST",
        "/v1/routes",
        {**BASE, "layer_mode": "manual", "altitude_m": 700},
    )
    assert status == 422 and err["details"][0]["field"] == "altitude_m"
    status, err, _ = call(
        "POST",
        "/v1/routes",
        {
            **BASE,
            "layer_mode": "manual",
            "altitude_m": 500,
            "constraints": {"altitude_range_m": [1000, 2000]},
        },
    )
    assert status == 422


def test_max_wind_speed_blocks_strong_station(call):
    # ایستگاه 58E با باد ≥ ۲۰ m/s تنها گذرگاه است؛ محدودیت ۱۰ آن را حذف می‌کند
    # (با max_edge پیش‌فرض ۲۰۰ کیلومتر، مسیر مستقیم 57→59 هم ممکن می‌ماند)
    status, body, _ = call(
        "POST", "/v1/routes", {**BASE, "constraints": {"max_wind_speed_mps": 10.0}}
    )
    assert status == 200
    assert pt(58.0) not in body["path"]


def test_max_wind_speed_too_strict_gives_no_feasible_path(call):
    status, err, _ = call(
        "POST", "/v1/routes", {**BASE, "constraints": {"max_wind_speed_mps": 1.0}}
    )
    assert status == 422 and err["code"] == "no_feasible_path"


def test_avoid_zone_node_edge_and_origin_rules(call):
    body = {"origin": pt(59.0), "destination": pt(60.0)}
    # منطقه دور از مسیر → بدون اثر
    far = {"type": "circle", "center": pt(57.0), "radius_km": 20}
    assert call("POST", "/v1/routes", {**body, "constraints": {"avoid_zones": [far]}})[0] == 200
    # منطقه روی گره 58 → مسیر 57→60 غیرممکن (هر دو یال عبوری از آن حذف می‌شوند)
    on_node = {"type": "circle", "center": pt(58.0), "radius_km": 20}
    status, err, _ = call("POST", "/v1/routes", {**BASE, "constraints": {"avoid_zones": [on_node]}})
    assert status == 422 and err["code"] == "no_feasible_path"
    # منطقه‌ای که فقط یال را قطع می‌کند (نه گره‌ها) هم مسیر را می‌بندد
    mid_edge = {"type": "circle", "center": pt(57.5), "radius_km": 10}
    status, err, _ = call("POST", "/v1/routes", {**BASE, "constraints": {"avoid_zones": [mid_edge]}})
    assert status == 422 and err["code"] == "no_feasible_path"
    # منطقه روی مبدأ
    on_origin = {"type": "circle", "center": pt(57.0), "radius_km": 5}
    status, err, _ = call(
        "POST", "/v1/routes", {**BASE, "constraints": {"avoid_zones": [on_origin]}}
    )
    assert status == 422 and err["code"] == "no_feasible_path"


def test_checkpoint_forces_waypoint(call):
    body = {"origin": pt(57.0), "destination": pt(59.0), "checkpoints": [{**pt(60.0), "order": 0}]}
    status, res, _ = call("POST", "/v1/routes", body)
    assert status == 200
    assert pt(60.0) in res["path"] and res["path"][-1] == pt(59.0)


def test_criteria_and_weights(call):
    for crit in ("time", "energy", "balanced"):
        c = {"criterion": crit}
        if crit == "balanced":
            c["weights"] = {"time": 0.7, "energy": 0.3}
        status, res, _ = call("POST", "/v1/routes", {**BASE, "constraints": c})
        assert status == 200 and res["criterion"] == crit


@pytest.mark.parametrize(
    "body,field",
    [
        ({}, "origin"),
        ({"origin": pt(57.0)}, "destination"),
        ({"origin": {"lat": 100, "lon": 0}, "destination": pt(58.0)}, "origin.lat"),
        ({"origin": {"lat": "x", "lon": 0}, "destination": pt(58.0)}, "origin.lat"),
        ({"origin": pt(57.0), "destination": pt(57.0)}, "destination"),
        ({**BASE, "algorithm": "bfs"}, "algorithm"),
        ({**BASE, "layer_mode": "manual"}, "altitude_m"),
        ({**BASE, "constraints": {"criterion": "cheap"}}, "constraints.criterion"),
        ({**BASE, "constraints": {"weights": {"time": 0.9, "energy": 0.9}}}, "constraints.weights"),
        ({**BASE, "constraints": {"max_wind_speed_mps": -3}}, "constraints.max_wind_speed_mps"),
        ({**BASE, "constraints": {"altitude_range_m": [2000, 500]}}, "constraints.altitude_range_m"),
        ({**BASE, "constraints": {"avoid_zones": [{"type": "box"}]}}, "constraints.avoid_zones[0]"),
        ({**BASE, "checkpoints": [{"lat": 999, "lon": 1}]}, "checkpoints[0].lat"),
        ({**BASE, "async": "yes"}, "async"),
    ],
)
def test_validation_errors_are_422_with_field(call, body, field):
    status, err, _ = call("POST", "/v1/routes", body)
    assert status == 422 and err["code"] == "validation_error"
    assert field in [d["field"] for d in err["details"]]
    assert err["request_id"]


def test_invalid_json_and_body_limits(app):
    status, _, out = app.handle("POST", "/v1/routes", b"{not json")
    assert status == 400 and b"invalid_json" in out
    assert app.handle("POST", "/v1/routes", b"")[0] == 400
    assert app.handle("POST", "/v1/routes", b"[]")[0] == 422
    assert app.handle("POST", "/v1/routes", b" " * 1_000_001)[0] == 413


def test_same_node_origin_destination_is_validation_error(call):
    body = {"origin": pt(57.0), "destination": pt(57.001)}
    status, err, _ = call("POST", "/v1/routes", body)
    assert status == 422 and err["details"][0]["field"] == "destination"


def test_async_job_lifecycle_and_events(app, call, bus):
    seen = []
    bus.subscribe(lambda e: seen.append(e.type))
    status, acc, _ = call("POST", "/v1/routes", {**BASE, "async": True})
    assert status == 202 and acc["poll_url"] == f"/v1/routes/jobs/{acc['job_id']}"
    for _ in range(200):
        _, job, _ = call("GET", acc["poll_url"].removeprefix("/v1") and acc["poll_url"])
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.01)
    assert job["status"] == "succeeded" and job["progress_pct"] == 100.0
    assert job["result"]["path"]
    assert call("GET", f"/v1/routes/jobs/{acc['job_id']}/compare-layers")[0] == 200
    assert seen[0] == "route.queued" and "route.running" in seen and seen[-1] == "route.succeeded"


def test_async_job_failure_reports_error(call):
    zone = {"type": "circle", "center": pt(57.0), "radius_km": 5}
    body = {**BASE, "async": True, "constraints": {"avoid_zones": [zone]}}
    _, acc, _ = call("POST", "/v1/routes", body)
    for _ in range(200):
        _, job, _ = call("GET", f"/v1/routes/jobs/{acc['job_id']}")
        if job["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.01)
    assert job["status"] == "failed" and job["error"]["code"] == "no_feasible_path"
    assert call("GET", "/v1/routes/jobs/job_unknown")[0] == 404
    assert call("GET", "/v1/routes/jobs/job_unknown/compare-layers")[0] == 404


def test_point_and_field_endpoints(call):
    status, s, _ = call("GET", "/v1/wind-layers/500/point?lat=36&lon=57")
    assert status == 200 and s["speed_mps"] == pytest.approx(5.0, abs=0.1)
    assert s["direction_deg"] == pytest.approx(90.0, abs=1.0)
    status, allp, _ = call("GET", "/v1/wind-layers/point-all?lat=36&lon=58.5")
    assert status == 200 and len(allp) == 4
    status, f, _ = call("GET", "/v1/wind-layers/500/field?resolutionDeg=1&bbox=57,36,60,36.5")
    assert status == 200 and len(f["vectors"]) == 4
    assert call("GET", "/v1/wind-layers/700/point?lat=36&lon=57")[0] == 404
    assert call("GET", "/v1/wind-layers/abc/point?lat=36&lon=57")[0] == 422
    assert call("GET", "/v1/wind-layers/500/point?lat=999&lon=57")[0] == 422
    assert call("GET", "/v1/wind-layers/500/point")[0] == 422
    assert call("GET", "/v1/wind-layers/500/field?resolutionDeg=0.0001")[0] == 422
    assert call("GET", "/v1/wind-layers/500/field?bbox=1,2,3")[0] == 422


def test_unknown_paths_methods_and_deferred(call, app):
    assert call("GET", "/v1/nope")[0] == 404
    assert call("GET", "/other")[0] == 404
    assert call("PUT", "/v1/algorithms")[0] == 405
    assert app.handle("OPTIONS", "/v1/routes")[0] == 204
    for method, template in DEFERRED_OPERATIONS:
        path = "/v1" + template.replace("{pointId}", "p1").replace("{provider}", "google")
        status, err, _ = call(method, path, {} if method in ("POST", "PUT", "PATCH") else None)
        assert status == 501 and err["code"] == "not_implemented", (method, template)


def test_all_openapi_operations_are_accounted_for():
    import re
    from pathlib import Path

    spec = (Path(__file__).resolve().parents[2] / "api" / "openapi.yaml").read_text()
    ops, cur = set(), None
    for line in spec.splitlines():
        m = re.match(r"^  (/[^:]*):", line)
        if m:
            cur = m.group(1)
        m2 = re.match(r"^    (get|post|put|patch|delete):", line)
        if m2 and cur:
            ops.add((m2.group(1).upper(), cur))
    assert ops == set(IMPLEMENTED_OPERATIONS) | set(DEFERRED_OPERATIONS)


def test_no_data_returns_503_and_never_crashes():
    import pandas as pd

    empty = WindDataProvider(pd.DataFrame(columns=["lat", "lon", "speed", "direction"]))
    app = ApiApp(empty)
    try:
        for method, path, body in [
            ("GET", "/v1/wind-layers", None),
            ("GET", "/v1/wind-layers/500/point?lat=36&lon=57", None),
            ("GET", "/v1/wind-layers/point-all?lat=36&lon=57", None),
            ("POST", "/v1/routes", b'{"origin":{"lat":36,"lon":57},"destination":{"lat":36,"lon":58}}'),
        ]:
            status, _, out = app.handle(method, path, body or b"")
            assert status == 503 and b"wind_data_unavailable" in out, path
        assert app.handle("GET", "/v1/algorithms")[0] == 200
    finally:
        app.close()


def test_real_khorasan_data_end_to_end():
    provider = WindDataProvider.from_csv()
    app = ApiApp(provider)
    try:
        import json

        st = provider._stations
        body = {
            "origin": {"lat": float(st.lat.iloc[0]), "lon": float(st.lon.iloc[0])},
            "destination": {"lat": float(st.lat.iloc[-1]), "lon": float(st.lon.iloc[-1])},
        }
        status, _, out = app.handle("POST", "/v1/routes", json.dumps(body).encode())
        res = json.loads(out)
        assert status == 200 and len(res["path"]) >= 2 and res["total_distance_km"] > 100
    finally:
        app.close()


def test_missing_data_file_is_503_error(tmp_path):
    from backend.errors import DataUnavailable

    with pytest.raises(DataUnavailable):
        WindDataProvider.from_csv(tmp_path / "missing.csv")


def test_real_http_server_smoke(provider):
    import json
    import threading
    import urllib.error
    import urllib.request

    from backend import serve

    server = serve("127.0.0.1", 0, provider)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        url = f"http://127.0.0.1:{port}/v1"
        with urllib.request.urlopen(url + "/algorithms") as r:
            assert r.status == 200 and json.load(r)["algorithms"]
        req = urllib.request.Request(
            url + "/routes", data=json.dumps(BASE).encode(), method="POST"
        )
        with urllib.request.urlopen(req) as r:
            assert r.status == 200 and json.load(r)["path"]
        bad = urllib.request.Request(url + "/routes", data=b"{}", method="POST")
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(bad)
        assert ei.value.code == 422
    finally:
        server.shutdown()
        server.server_close()
        server.app.close()
