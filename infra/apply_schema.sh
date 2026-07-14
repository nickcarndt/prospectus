#!/usr/bin/env bash
# Apply infra/schema.sql to the local Prospectus Postgres.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="$ROOT/infra/docker-compose.yml"

if ! docker compose -f "$COMPOSE" ps --status running 2>/dev/null | grep -q postgres; then
  echo "Starting postgres via docker compose..."
  docker compose -f "$COMPOSE" up -d
fi

echo "Waiting for postgres health..."
for _ in $(seq 1 30); do
  if docker exec prospectus-postgres pg_isready -U prospectus -d prospectus >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec -i prospectus-postgres psql -U prospectus -d prospectus < "$ROOT/infra/schema.sql"
docker exec -i prospectus-postgres psql -U prospectus -d prospectus < "$ROOT/infra/schema_fts.sql"
echo "Schema applied."
docker exec prospectus-postgres psql -U prospectus -d prospectus -c "\d chunks"
