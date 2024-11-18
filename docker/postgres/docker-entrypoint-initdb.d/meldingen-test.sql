CREATE DATABASE "meldingen-test";
\c "meldingen-test";
CREATE EXTENSION IF NOT EXISTS postgis;
GRANT ALL PRIVILEGES ON DATABASE "meldingen-test" to meldingen;
