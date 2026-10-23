# NammaMove — Disruption-Aware Mobility Platform

Independent, clean-start implementation for Bengaluru-first, multimodal journey recovery. **This is an initial working backend simulator**, not the complete Moovit-like app or a real-time transit service. It does not reuse code from the reference repository.

## Quickstart — Windows PowerShell

Install Python 3.12+ and Git. In the project directory:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/docs` to try endpoints.

If PowerShell blocks activation, run `.venv\Scripts\python.exe -m pytest -q` and `.venv\Scripts\python.exe -m uvicorn app.main:app --reload` without activating.

## Sample disruption request

POST `/journeys/plan` with JSON:

```json
{"origin":"Electronic City","destination":"MG Road","incidents":[{"id":"closure-demo","affected_edges":["bus-2"],"kind":"road_closure","verified":true,"blocked":true}]}
```

The system replans around the blocked edge. Unverified incidents are **not** treated as confirmed blocks. This simple implementation is deterministic and **not** a full GTFS journey planner.

## Architectural roadmap

1. **Phase 1:** Schema (PostgreSQL/PostGIS), GTFS import, OpenTripPlanner, mobile app in Expo, maps and accessible trip planning.
2. **Phase 2:** GTFS-RT adapters, event ingestion, feed freshness, confirmed/unconfirmed incidents, authenticated WebSocket notifications and automatic trip recovery.
3. **Phase 3:** Calibrated ETA and connection-risk models, route reliability uncertainty ranges, model monitoring.
4. **Phase 4:** Capacity-aware rerouting, impact radius, load balancing and operator digital twin.
5. **Phase 5:** Accessible offline navigation, multilingual voice features, verified partner ticketing and payment settlements.

### Required engineering invariants

- Absence of GPS data must never be classified as cancellation without separate credible evidence.
- Incident verification and source freshness are recorded separately.
- Unverified reports may warn riders but may not close network edges automatically.
- A route must honor direction, accessibility constraints, capacity signals, and genuine transfer feasibility.
- Replanning needs hysteresis/cooldowns and user confirmation to avoid oscillation.
- No simulated information should appear in the UI as real-time feed data.
- Tickets, balances and payments require authorization and verified settlement, never direct arbitrary top-ups.
- Use data minimization, short retention and consent for location sharing.

## Reference and provenance

The former Namma-Yatra repository was reviewed for requirements and gaps but its source was **not copied**. This project contains no Replit-specific dependencies or configuration. Preserve truthful attribution and licensing wherever any third-party code or assets are subsequently reused; do not misrepresent development history.

## Repository layout

- `backend/app/engine.py`: bounded sample routing algorithm
- `backend/app/main.py`: FastAPI API
- `backend/tests/test_engine.py`: initial regression tests
- `docs/`: architecture, feature catalogue and fault scenarios
- `compose.yaml`: optional local PostGIS and Redis services (not yet used by the simulator)
