#!/usr/bin/env bash
# Seed Vault cho CineHome app (shared Redis/Postgres với banking — KHÔNG ghi đè secret infra).
#
# Movie DB password (riêng CineHome):
#   MOVIE_DB_PASSWORD=Tech1604
#
# Redis: mặc định KHÔNG password trong URL (redis://host:6379/0).
# Nếu Redis bật AUTH, set REDIS_PASSWORD=...
#
#   oc exec -i -n vault vault-0 -- env \
#     VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=root \
#     MOVIE_DB_PASSWORD=... \
#     bash -s < scripts/vault-seed-cinehome-secrets.sh
set -euo pipefail

: "${VAULT_ADDR:=http://127.0.0.1:8200}"
: "${VAULT_TOKEN:?set VAULT_TOKEN}"
: "${MOVIE_DB_PASSWORD:?set MOVIE_DB_PASSWORD}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

export VAULT_ADDR VAULT_TOKEN

PG_HOST="${PG_HOST:-postgres-ha-postgresql-primary.postgres.svc.cluster.local}"
REDIS_HOST="${REDIS_HOST:-redis-ha.redis.svc.cluster.local}"

DATABASE_URL="postgresql+psycopg2://movie:${MOVIE_DB_PASSWORD}@${PG_HOST}:5432/movie"
if [[ -n "${REDIS_PASSWORD}" ]]; then
  REDIS_URL="redis://:${REDIS_PASSWORD}@${REDIS_HOST}:6379/0"
else
  REDIS_URL="redis://${REDIS_HOST}:6379/0"
fi

echo "==> secret/cinehome/movie-db (user movie trên shared postgres)"
vault kv put secret/cinehome/movie-db \
  username='movie' \
  password="${MOVIE_DB_PASSWORD}" \
  database='movie'

echo "==> secret/cinehome/app  REDIS_URL=${REDIS_URL}"
if [[ -n "${MINIO_ROOT_USER:-}" && -n "${MINIO_ROOT_PASSWORD:-}" ]]; then
  vault kv put secret/cinehome/app \
    DATABASE_URL="${DATABASE_URL}" \
    REDIS_URL="${REDIS_URL}" \
    MINIO_ACCESS_KEY="${MINIO_ROOT_USER}" \
    MINIO_SECRET_KEY="${MINIO_ROOT_PASSWORD}"
  echo "==> secret/cinehome/minio"
  vault kv put secret/cinehome/minio \
    rootUser="${MINIO_ROOT_USER}" \
    rootPassword="${MINIO_ROOT_PASSWORD}"
else
  vault kv put secret/cinehome/app \
    DATABASE_URL="${DATABASE_URL}" \
    REDIS_URL="${REDIS_URL}" \
    MINIO_ACCESS_KEY='SET_AFTER_MINIO' \
    MINIO_SECRET_KEY='SET_AFTER_MINIO'
  echo "(skip minio — set MINIO_ROOT_USER/PASSWORD rồi chạy lại)"
fi

echo "OK — không đụng secret/banking/* hay redis-ha / postgres-ha-postgresql"
vault kv metadata get secret/cinehome/app >/dev/null
