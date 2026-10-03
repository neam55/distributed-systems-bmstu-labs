#!/usr/bin/env bash
set -e

# Вариант задания 2 — Hotels Booking System.
export VARIANT="v2"
export SCRIPT_PATH=/docker-entrypoint-initdb.d/
export PGPASSWORD=postgres
psql -f "$SCRIPT_PATH/scripts/db-$VARIANT.sql"
