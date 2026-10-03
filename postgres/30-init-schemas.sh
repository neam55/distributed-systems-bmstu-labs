#!/usr/bin/env bash
set -e

# Схемы и тестовые данные для каждой логической базы. Запросы между базами запрещены,
# поэтому каждый файл применяется в свою базу отдельным подключением.
export SCRIPT_PATH=/docker-entrypoint-initdb.d/
export PGPASSWORD=postgres

for db in reservations payments loyalties; do
  echo "Initializing schema for database '$db'..."
  psql -v ON_ERROR_STOP=1 -d "$db" -f "$SCRIPT_PATH/scripts/$db.sql"
done
