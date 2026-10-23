"""Small deterministic transit engine. SAMPLE NETWORK ONLY; not live BMTC data."""
from dataclasses import dataclass, asdict
from heapq import heappush, heappop
from typing import Literal

Status = Literal['scheduled', 'delayed', 'uncertain', 'confirmed_cancelled']
Feed = Literal['live', 'stale', 'unavailable', 'simulation']

@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    mode: str
    minutes: int
    fare: float
    capacity: int = 100
    demand: int = 0
    status: Status = 'scheduled'
    feed: Feed = 'simulation'

EDGES = [
    Edge('bus-1','Electronic City','Silk Board','bus',26,25),
    Edge('bus-2','Silk Board','Majestic','bus',38,25),
    Edge('metro-1','Majestic','MG Road','metro',12,20),
    Edge('bus-3','Electronic City','BTM Layout','bus',29,20),
    Edge('bus-4','BTM Layout','MG Road','bus',55,30),
    Edge('walk-1','Silk Board','BTM Layout','walk',21,0),
    Edge('metro-2','MG Road','Majestic','metro',12,20),
]

@dataclass(frozen=True)
class Incident:
    id: str
    affected_edges: tuple[str, ...]
    kind: str
    verified: bool
    delay_minutes: int = 0
    blocked: bool = False


def route(start: str, end: str, incidents: list[Incident] | None = None, edges: list[Edge] | None = None):
    """Direction-aware, minimum-duration route. Demo only; NOT schedule-aware GTFS routing."""
    incidents = incidents or []
    edges = edges if edges is not None else EDGES
    adjacency: dict[str, list[tuple[str,int,Edge]]] = {}
    for edge in edges:
        if edge.status == 'confirmed_cancelled':
            continue
        matching = [i for i in incidents if i.verified and edge.id in i.affected_edges]
        if any(i.blocked for i in matching):
            continue
        # Unknown vehicle position != cancellation. Unknown services remain candidates but are penalized.
        uncertainty_penalty = 15 if edge.status == 'uncertain' or edge.feed in ('stale', 'unavailable') else 0
        capacity_penalty = 20 if edge.demand >= edge.capacity else 0
        added_delay = sum(max(0, i.delay_minutes) for i in matching)
        weight = edge.minutes + uncertainty_penalty + capacity_penalty + added_delay
        adjacency.setdefault(edge.source, []).append((edge.target, weight, edge))
    queue = [(0, 0, start, [])]
    best = {start: 0}
    serial = 0
    while queue:
        total, _, current, legs = heappop(queue)
        if total != best.get(current):
            continue
        if current == end:
            return {'origin':start,'destination':end,'estimatedMinutes':total,
                    'fare':sum(e.fare for e in legs), 'legs':[asdict(e) for e in legs],
                    'dataNotice':'Illustrative simulated network, not verified live transit data.'}
        for target, minutes, edge in adjacency.get(current, []):
            candidate = total + minutes
            if candidate < best.get(target, float('inf')):
                best[target] = candidate
                serial += 1
                heappush(queue, (candidate, serial, target, legs + [edge]))
    return None


def service_state(last_seen_seconds: int | None, operator_cancelled: bool = False) -> tuple[Status, Feed]:
    if operator_cancelled:
        return ('confirmed_cancelled', 'unavailable')
    if last_seen_seconds is None:
        return ('uncertain', 'unavailable')
    if last_seen_seconds > 300:
        return ('uncertain', 'stale')
    return ('scheduled', 'live')
