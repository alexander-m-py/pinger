#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE TABLE pinger_data(
        id serial PRIMARY KEY,
        host VARCHAR(50) NOT NULL,
        ping_timestamp TIMESTAMP NOT NULL,
        result BOOLEAN NOT NULL
    );
EOSQL
