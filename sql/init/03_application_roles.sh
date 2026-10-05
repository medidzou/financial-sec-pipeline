#!/bin/sh
set -eu

: "${DASHBOARD_DB_USER:?DASHBOARD_DB_USER doit être défini dans .env}"
: "${DASHBOARD_DB_PASSWORD:?DASHBOARD_DB_PASSWORD doit être défini dans .env}"
: "${ETL_DB_USER:?ETL_DB_USER doit être défini dans .env}"
: "${ETL_DB_PASSWORD:?ETL_DB_PASSWORD doit être défini dans .env}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=dashboard_user="$DASHBOARD_DB_USER" \
    --set=dashboard_password="$DASHBOARD_DB_PASSWORD" \
    --set=etl_user="$ETL_DB_USER" \
    --set=etl_password="$ETL_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN', :'dashboard_user')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'dashboard_user')
\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'dashboard_user', :'dashboard_password')
\gexec
SELECT format('CREATE ROLE %I LOGIN', :'etl_user')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'etl_user')
\gexec
SELECT format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'etl_user', :'etl_password')
\gexec

SELECT format(
    'GRANT CONNECT ON DATABASE %I TO %I, %I',
    current_database(),
    :'dashboard_user',
    :'etl_user'
)
\gexec
GRANT USAGE ON SCHEMA public TO :"dashboard_user", :"etl_user";

GRANT SELECT ON assets, asset_prices, indicators, audit_logs, users
    TO :"dashboard_user";
GRANT INSERT ON audit_logs TO :"dashboard_user";
GRANT SELECT, INSERT, UPDATE, DELETE ON login_attempts TO :"dashboard_user";
GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO :"dashboard_user";

GRANT SELECT, INSERT, UPDATE ON assets, asset_prices, indicators TO :"etl_user";
GRANT INSERT ON audit_logs TO :"etl_user";
GRANT USAGE, SELECT ON SEQUENCE assets_id_seq, asset_prices_id_seq,
    indicators_id_seq, audit_logs_id_seq TO :"etl_user";
SQL