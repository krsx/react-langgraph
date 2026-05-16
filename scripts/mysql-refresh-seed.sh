#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SEED_FILE="${REPO_ROOT}/backend/db/seed.sql"
MYSQL_SERVICE="mysql"

usage() {
  cat <<'EOF'
Usage: ./scripts/mysql-refresh-seed.sh

Drops and recreates the configured MySQL database in the running Docker Compose
mysql service, then replays backend/db/seed.sql to restore fresh demo data.

Prerequisites:
  - docker compose is installed
  - the mysql service is already running
EOF
}

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
}

ensure_seed_file() {
  if [[ ! -f "${SEED_FILE}" ]]; then
    echo "Seed file not found: ${SEED_FILE}" >&2
    exit 1
  fi
}

ensure_mysql_running() {
  if ! docker compose ps --status running --services | grep -Fxq "${MYSQL_SERVICE}"; then
    cat >&2 <<'EOF'
MySQL service is not running.
Start it first with: docker compose up -d mysql
EOF
    exit 1
  fi
}

wait_for_mysql() {
  docker compose exec -T "${MYSQL_SERVICE}" sh -lc '
    mysqladmin ping -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" >/dev/null
  '
}

refresh_database() {
  docker compose exec -T "${MYSQL_SERVICE}" sh -lc '
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "
      DROP DATABASE IF EXISTS \`${MYSQL_DATABASE}\`;
      CREATE DATABASE \`${MYSQL_DATABASE}\`;
    "
  '
}

seed_database() {
  docker compose exec -T "${MYSQL_SERVICE}" sh -lc '
    mysql -u root -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}"
  ' < "${SEED_FILE}"
}

print_summary() {
  docker compose exec -T "${MYSQL_SERVICE}" sh -lc '
    mysql -N -u root -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" -e "
      SELECT '\''customers'\'', COUNT(*) FROM customers
      UNION ALL
      SELECT '\''orders'\'', COUNT(*) FROM orders
      UNION ALL
      SELECT '\''complaints'\'', COUNT(*) FROM complaints
      UNION ALL
      SELECT '\''customer_memory'\'', COUNT(*) FROM customer_memory;
    "
  '
}

main() {
  if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
  fi

  require_command docker
  ensure_seed_file
  ensure_mysql_running

  echo "Waiting for MySQL to respond..."
  wait_for_mysql

  echo "Dropping and recreating database..."
  refresh_database

  echo "Replaying seed data from ${SEED_FILE}..."
  seed_database

  echo "Fresh seed complete. Row counts:"
  print_summary
}

main "$@"
