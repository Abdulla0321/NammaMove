# Architecture decisions
## ADR-001 ? Flatten existing starter wrapper (accepted, Phase 00)
The wrapper contained all source with no independent package purpose. Move its contents into the existing Git root, preserve history and backlog, and update commands. No new repository or project is created.

## ADR-002 ? Modular monolith and progressive stack (accepted)
Retain FastAPI and the simulator. Add database/auth, OTP, clients, realtime and ML in their phases. Compose services remain optional and disconnected for now. Avoid premature services and unused dependencies.

## ADR-003 ? Separate truth from freshness (accepted)
Missing GPS cannot establish cancellation. Production verification needs authorized evidence, confidence and expiry. Preserve demo flags for compatibility, clearly labeled; replace their trust boundary before live deployment.

## ADR-004 ? Congestion is a release constraint (accepted)
Static crowding penalties are illustrative, not network assignment. Require aggregate replay, capacity-aware throttling and cooldown before live automatic recovery. Individual shortest paths do not prove network safety.

## ADR-005 ? Foundation quality gates (accepted)
Use pytest/HTTPX, Ruff lint/format and strict mypy for application code. CI spans Windows/Linux, Python 3.12/3.14. Separate runtime/dev requirements. TypeScript gates start when clients exist. Current dependency bounds are not locks; reviewed reproducible locks and vulnerability scans are required before release.

## ADR-006 ? Environment independence (accepted)
No Replit dependency/configuration exists, so no replacement is needed. Use standard Python/Uvicorn and optional Docker. Simulator needs no secrets. Compose requires an ignored local password; future URLs remain documented, unconnected configuration. Ignore rules do not prove tracked content is secret-free.
