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
