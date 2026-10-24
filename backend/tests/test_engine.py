from app.engine import Edge, Incident, route, service_state


def test_baseline_route():
    assert [leg["id"] for leg in route("Electronic City", "MG Road")["legs"]] == [
        "bus-1",
        "bus-2",
        "metro-1",
    ]


def test_verified_block_replans():
    incident = Incident("closure-1", ("bus-2",), "road_closure", True, blocked=True)
    assert [leg["id"] for leg in route("Electronic City", "MG Road", [incident])["legs"]] == [
        "bus-3",
        "bus-4",
    ]


def test_unverified_block_does_not_remove_network_link():
    incident = Incident("rumor", ("bus-2",), "road_closure", False, blocked=True)
    assert "bus-2" in [leg["id"] for leg in route("Electronic City", "MG Road", [incident])["legs"]]


def test_missing_gps_is_not_cancellation():
    assert service_state(None) == ("uncertain", "unavailable")
    assert service_state(900) == ("uncertain", "stale")
    assert service_state(None, True)[0] == "confirmed_cancelled"


def test_directionality():
    assert route("MG Road", "Electronic City") is None


def test_capacity_penalty_avoids_overcrowded_alternative():
    edges = [
        Edge("crowded", "A", "B", "bus", 10, 5, capacity=10, demand=20),
        Edge("less-crowded", "A", "B", "bus", 16, 5, capacity=30, demand=5),
    ]
    assert route("A", "B", edges=edges)["legs"][0]["id"] == "less-crowded"


def test_verified_delay_replans():
    incident = Incident("delay-1", ("bus-2",), "delay", True, delay_minutes=50)
    assert [leg["id"] for leg in route("Electronic City", "MG Road", [incident])["legs"]] == [
        "bus-3",
        "bus-4",
    ]
