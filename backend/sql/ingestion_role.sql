-- Explicit owner-run provisioning AFTER 0003; not executed by migrations/startup.
-- No login or credentials are created; review and assign an existing dedicated login.
CREATE ROLE nammamove_ingestion NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT USAGE ON SCHEMA nammamove TO nammamove_ingestion;
GRANT SELECT ON nammamove.ingestion_sources, nammamove.ingestion_generations TO nammamove_ingestion;
GRANT INSERT ON nammamove.ingestion_generations TO nammamove_ingestion;
GRANT UPDATE (header_at, fingerprint, received_at, checkpoint, checkpoint_digest, guards_digest) ON nammamove.ingestion_sources TO nammamove_ingestion;
GRANT SELECT ON nammamove.transit_feeds, nammamove.transit_datasets, nammamove.gtfs_trips, nammamove.gtfs_services, nammamove.gtfs_calendar_dates TO nammamove_ingestion;
-- Existing catalog RLS still requires verified transaction-local worker identity.
-- This small slice uses the maintenance owner; dedicated worker identity/grant
-- acceptance must be completed before a non-owner worker is enabled.
