# Architecture: implementation intent

Mobile: Expo + React Native + TypeScript. Admin: React + TypeScript. API: FastAPI + Pydantic. Storage: PostgreSQL/PostGIS. Cache/jobs: Redis + background workers. Routing: OpenTripPlanner on authorized GTFS and OSM feeds. Predictive ML: scikit-learn/XGBoost, model-calibrated uncertainty. Events: durable incident store, deduplicated subscriptions, FCM notifications and WebSockets. Observability: OpenTelemetry/Prometheus/Grafana. Deploy with Docker and CI before evaluating Kubernetes.

Core tables to introduce: operators, stops, stop_times, trips, routes, shapes, realtime_vehicle_positions, feed_snapshots, service_alerts, incidents, incident_evidence, graph_overrides, journey_plans, active_journeys, user_preferences, report_moderation, notifications, tickets, payments and audit_events.

Do not equate unavailable position feeds with cancellation. Feed status (live/stale/unavailable) and operational status (scheduled/delayed/uncertain/confirmed_cancelled) are independent. Graph modifications require credible evidence and expire or are explicitly resolved. Replan only at feasible transition points; rank by expected delay, risk, fare, accessibility and congestion externality. Explain the recommendation in plain language and never force an irreversible booking or payment.

Threat model: input validation, role separation, short-lived access tokens, scoped database permissions, privacy-minimizing telemetry, rate limits, opt-in location sharing, authenticated provider ingestion, signed webhook verification, financial ledger integrity, incident audit trail. Test before real-world use.
