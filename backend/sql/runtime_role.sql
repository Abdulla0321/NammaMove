-- Run once as database administrator after migrations, using psql.
-- This is a non-login privilege group; assign it to a separate runtime login.
-- No passwords are stored here. Do not run the API as schema owner or superuser.
CREATE ROLE nammamove_api NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA nammamove TO nammamove_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA nammamove TO nammamove_api;
REVOKE ALL ON nammamove.alembic_version FROM nammamove_api;
GRANT SELECT ON nammamove.alembic_version TO nammamove_api;
REVOKE UPDATE, DELETE ON nammamove.audit_events, nammamove.disruption_evidence FROM nammamove_api;
-- Provision a login interactively using CREATE ROLE and psql \password; then:
-- GRANT nammamove_api TO your_runtime_login;
-- New migrations must explicitly review and grant permissions for new tables.

-- Static transit imports are maintenance-owner operations, never API writes.
REVOKE INSERT, UPDATE, DELETE ON nammamove.gtfs_agencies, nammamove.gtfs_calendar_dates, nammamove.gtfs_frequencies, nammamove.gtfs_routes, nammamove.gtfs_services, nammamove.gtfs_shape_points, nammamove.gtfs_shapes, nammamove.gtfs_stop_times, nammamove.gtfs_stops, nammamove.gtfs_transfers, nammamove.gtfs_trips, nammamove.transit_datasets, nammamove.transit_feeds FROM nammamove_api;
