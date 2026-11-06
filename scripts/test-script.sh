#!/usr/bin/env bash
set -euo pipefail
variant=${1:-${VARIANT:-v2}}
service=${2:-${SERVICE_NAME:-loyalty-service}}
port=${3:-${PORT_NUMBER:-8050}}
path=$(dirname "$0")
environment=$(mktemp)
cp "$variant/postman/environment.json" "$environment"
cleanup() {
  docker compose start "$service" >/dev/null || true
  rm -f "$environment"
}
trap cleanup EXIT
run_folder() {
  newman run --delay-request 100 --folder "$1" \
    --environment "$environment" --export-environment "$environment" \
    "$variant/postman/collection.json"
}
run_folder success
for step in 1 2 3 4; do
  if (( step % 2 )); then
    docker compose stop "$service"
  else
    docker compose start "$service"
    sh "$path/wait-for.sh" -t 120 "http://localhost:$port/manage/health"
  fi
  run_folder "step$step"
done
