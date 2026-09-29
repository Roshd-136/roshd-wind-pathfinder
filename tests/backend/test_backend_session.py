"""تست‌های مدیریت حالت، سیستم رویداد و اتصال کامل کنترل‌های UI."""

import pytest
from conftest import pt

from backend import EventBus
from backend.errors import ApiError, ValidationFailed
from backend.events import Event
from backend.wiring import UI_CONTROLS, verify_wiring


def test_wiring_is_complete():
    assert verify_wiring() == []


def test_every_control_action_executes_without_dead_ends(session):
    """هر کنترل ثبت‌شده باید اکشن قابل‌اجرا و نتیجه قابل‌نمایش داشته باشد (بدون دکمه مرده)."""
    payloads = {
        "set_origin": pt(57.0),
        "set_destination": pt(60.0),
        "swap_endpoints": {},
        "add_checkpoint": pt(59.0),
        "remove_checkpoint": {"index": 0},
        "set_algorithm": {"algorithm": "dijkstra"},
        "set_criterion": {"criterion": "balanced", "time_weight": 0.6},
        "set_time_weight": {"time_weight": 0.4},
        "set_layer_mode": {"layer_mode": "manual"},
        "set_altitude": {"altitude_m": 1000},
        "toggle_layer_visibility": {"altitude_m": 500},
        "set_max_wind_speed": {"max_wind_speed_mps": 30},
        "set_altitude_range": {"altitude_range_m": [500, 2000]},
        "add_avoid_zone": {"center": pt(57.5, 37.0), "radius_km": 5},
        "remove_avoid_zone": {"index": 0},
        "reset_filters": {},
        "point_info": {**pt(58.0), "altitude_m": 500},
        "point_info_all": pt(58.0),
    }
    for c in UI_CONTROLS:
        if c.action is None or c.action in ("calculate", "compare_layers", "reset"):
            continue
        if c.action == "remove_checkpoint":
            session.dispatch("add_checkpoint", pt(59.0))
        if c.action == "remove_avoid_zone":
            session.dispatch("add_avoid_zone", payloads["add_avoid_zone"])
        assert session.dispatch(c.action, payloads[c.action]) is not None, c.control_id
    # حالت را برای اجرا مرتب می‌کنیم: دکمه اجرا و مقایسه لایه‌ها
    session.dispatch("reset", {})
    session.dispatch("set_origin", pt(57.0))
    session.dispatch("set_destination", pt(60.0))
    state = session.dispatch("calculate", {})
    assert state["last_result"]["path"] and state["last_error"] is None
    cmp_ = session.dispatch("compare_layers", {})
    assert any(r["is_best"] for r in cmp_["rows"])
    assert session.dispatch("reset", {})["last_result"] is None


def test_state_maps_to_route_request_parameters(session):
    session.dispatch("set_origin", pt(57.0))
    session.dispatch("set_destination", pt(60.0))
    session.dispatch("add_checkpoint", pt(59.0))
    session.dispatch("set_algorithm", {"algorithm": "dijkstra"})
    session.dispatch("set_criterion", {"criterion": "balanced", "time_weight": 0.25})
    session.dispatch("set_altitude", {"altitude_m": 1500})
    session.dispatch("set_max_wind_speed", {"max_wind_speed_mps": 40})
    session.dispatch("add_avoid_zone", {"center": pt(58.0, 37.0), "radius_km": 10})
    body = session.build_request()
    assert body["algorithm"] == "dijkstra" and body["layer_mode"] == "manual"
    assert body["altitude_m"] == 1500 and body["checkpoints"][0]["order"] == 0
    assert body["constraints"]["weights"] == {"time": 0.25, "energy": 0.75}
    assert body["constraints"]["max_wind_speed_mps"] == 40
    assert len(body["constraints"]["avoid_zones"]) == 1
    result = session.dispatch("calculate", {})["last_result"]
    assert result["algorithm"] == "dijkstra" and result["layer_altitude_m"] == 1500
    assert result["criterion"] == "balanced"


def test_calculate_without_endpoints_is_validation_error_and_recorded(session):
    with pytest.raises(ValidationFailed) as ei:
        session.dispatch("calculate", {})
    assert {i.field for i in ei.value.issues} >= {"origin", "destination"}
    assert session.state["last_error"]["code"] == "validation_error"
    assert session.state["last_result"] is None


def test_calculate_no_feasible_path_recorded(session):
    session.dispatch("set_origin", pt(57.0))
    session.dispatch("set_destination", pt(60.0))
    session.dispatch("set_max_wind_speed", {"max_wind_speed_mps": 1})
    with pytest.raises(ApiError):
        session.dispatch("calculate", {})
    assert session.state["last_error"]["code"] == "no_feasible_path"


def test_compare_layers_requires_a_route(session):
    with pytest.raises(ValidationFailed):
        session.dispatch("compare_layers", {})


@pytest.mark.parametrize(
    "action,payload",
    [
        ("set_origin", {"lat": 200, "lon": 0}),
        ("set_origin", {}),
        ("set_algorithm", {"algorithm": "x"}),
        ("set_criterion", {"criterion": "x"}),
        ("set_time_weight", {"time_weight": 2}),
        ("set_layer_mode", {"layer_mode": "x"}),
        ("set_altitude", {"altitude_m": 12345}),
        ("set_altitude", {"altitude_m": "a"}),
        ("toggle_layer_visibility", {"altitude_m": 12345}),
        ("set_max_wind_speed", {"max_wind_speed_mps": 0}),
        ("set_altitude_range", {"altitude_range_m": [5, 1]}),
        ("add_avoid_zone", {"center": pt(1.0), "radius_km": -1}),
        ("remove_avoid_zone", {"index": 3}),
        ("remove_checkpoint", {"index": 0}),
        ("point_info", {**pt(58.0), "altitude_m": 42}),
        ("point_info_all", {"lat": "x"}),
        ("no_such_action", {}),
    ],
)
def test_invalid_control_input_is_rejected_and_state_unchanged(session, action, payload):
    before = session.state
    with pytest.raises(ValidationFailed):
        session.dispatch(action, payload)
    assert session.state == before


def test_layer_mode_auto_clears_altitude_and_visibility_toggles(session):
    session.dispatch("set_altitude", {"altitude_m": 1000})
    assert session.state["layer_mode"] == "manual"
    session.dispatch("set_layer_mode", {"layer_mode": "auto"})
    assert session.state["altitude_m"] is None
    session.dispatch("toggle_layer_visibility", {"altitude_m": 1500})
    session.dispatch("toggle_layer_visibility", {"altitude_m": 500})
    assert session.state["visible_layers"] == [500.0, 1500.0]
    session.dispatch("toggle_layer_visibility", {"altitude_m": 500})
    assert session.state["visible_layers"] == [1500.0]


def test_swap_and_state_is_copy(session):
    session.dispatch("set_origin", pt(57.0))
    session.dispatch("set_destination", pt(60.0))
    session.dispatch("swap_endpoints", {})
    assert session.state["origin"] == pt(60.0)
    snap = session.state
    snap["origin"] = None
    assert session.state["origin"] == pt(60.0)


def test_state_changed_events_published(session):
    events = []
    session.bus.subscribe(events.append, "state.changed")
    session.dispatch("set_algorithm", {"algorithm": "dijkstra"})
    assert events[0].payload["action"] == "set_algorithm"
    assert events[0].payload["state"]["algorithm"] == "dijkstra"


def test_async_calculate_sets_pending_job(session):
    session.dispatch("set_origin", pt(57.0))
    session.dispatch("set_destination", pt(60.0))
    state = session.dispatch("calculate", {"async": True})
    assert state["pending_job_id"].startswith("job_")
    session.service.shutdown()


def test_event_bus_isolation_and_unsubscribe():
    bus = EventBus()
    got = []

    def bad(_):
        raise RuntimeError("boom")

    bus.subscribe(bad)
    unsub = bus.subscribe(got.append, "a")
    bus.publish(Event("a", {"x": 1}))
    bus.publish(Event("b"))
    assert [e.type for e in got] == ["a"] and len(bus.errors) == 2
    unsub()
    bus.publish(Event("a"))
    assert len(got) == 1
