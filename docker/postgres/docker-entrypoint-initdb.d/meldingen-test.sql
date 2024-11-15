CREATE DATABASE "meldingen-test";
\c "meldingen-test";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
-- Reconnect to update pg_setting.resetval
-- See https://github.com/postgis/docker-postgis/issues/288
\c "meldingen-test";
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;
GRANT ALL PRIVILEGES ON DATABASE "meldingen-test" to meldingen;
