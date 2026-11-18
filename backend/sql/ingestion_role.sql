-- Explicit owner-run provisioning AFTER 0005; not executed by migrations/startup.
-- No login or credentials are created; review and assign an existing dedicated login.
CREATE ROLE nammamove_ingestion NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA nammamove TO nammamove_ingestion;
GRANT SELECT ON nammamove.ingestion_sources, nammamove.ingestion_generations TO nammamove_ingestion;
GRANT INSERT ON nammamove.ingestion_generations TO nammamove_ingestion;
GRANT DELETE ON nammamove.ingestion_generations TO nammamove_ingestion;
GRANT SELECT ON nammamove.ingestion_workers TO nammamove_ingestion;
GRANT SELECT, INSERT, DELETE ON nammamove.ingestion_dispatch TO nammamove_ingestion;
GRANT UPDATE (state, attempts, due_at, token, lease_until) ON nammamove.ingestion_dispatch TO nammamove_ingestion;
GRANT UPDATE (header_at, fingerprint, received_at, checkpoint, checkpoint_digest, guards_digest) ON nammamove.ingestion_sources TO nammamove_ingestion;
GRANT SELECT ON nammamove.transit_feeds, nammamove.transit_datasets, nammamove.gtfs_trips, nammamove.gtfs_services, nammamove.gtfs_calendar_dates TO nammamove_ingestion;
-- Owner alone registers sources and assigns exact current_user names:
-- INSERT INTO nammamove.ingestion_workers(worker_name,source_id) VALUES (...,...);
-- Assign this group to a dedicated non-owner/non-BYPASSRLS login. Never grant
-- membership in other worker logins, API, owner or privileged roles. SET ROLE
-- to this shared group intentionally has no source assignment and fails closed.
