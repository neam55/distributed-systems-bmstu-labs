#!/usr/bin/env bash
set -euo pipefail
path=$(dirname "$0")
environment=$(mktemp)
cp v2/postman/environment.json "$environment"
cleanup() {
  docker compose start payment-service reservation-service >/dev/null || true
  rm -f "$environment"
}
trap cleanup EXIT
run_folder() {
  newman run --folder "$1" --environment "$environment" \
    --export-environment "$environment" v2/postman/fault-tolerance.collection.json
}
run_folder setup
docker compose stop payment-service
run_folder payment-down
docker compose start payment-service
sh "$path/wait-for.sh" -t 120 http://localhost:8060/manage/health
sleep "${CB_RECOVERY_TIMEOUT:-5}"
run_folder recovered
docker compose stop reservation-service
run_folder reservation-down
docker compose start reservation-service
sh "$path/wait-for.sh" -t 120 http://localhost:8070/manage/health
sleep "${CB_RECOVERY_TIMEOUT:-5}"
run_folder recovered
