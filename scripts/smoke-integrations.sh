#!/usr/bin/env bash

set -euo pipefail

log_info() { printf '[INFO] %s\n' "$1"; }
log_ok() { printf '[OK] %s\n' "$1"; }
log_err() { printf '[ERROR] %s\n' "$1" >&2; }

if [ -z "${LOKI_URL:-}" ]; then
    log_err "LOKI_URL no está exportada."
    exit 1
fi
if [ -z "${RESTIC_PASSWORD:-}" ] && [ -n "${RESTIC_PASSWORD_FILE:-}" ]; then
    if [ ! -r "${RESTIC_PASSWORD_FILE}" ]; then
        log_err "No se puede leer el archivo configurado en RESTIC_PASSWORD_FILE."
        exit 1
    fi
    RESTIC_PASSWORD="$(<"${RESTIC_PASSWORD_FILE}")"
    export RESTIC_PASSWORD
fi
if [ -z "${RESTIC_REPOSITORY:-}" ] || [ -z "${RESTIC_PASSWORD:-}" ]; then
    log_err "Configura RESTIC_REPOSITORY y RESTIC_PASSWORD en el entorno."
    exit 1
fi
if ! command -v curl >/dev/null 2>&1 || ! command -v restic >/dev/null 2>&1; then
    log_err "Se requieren curl y restic para la prueba de integración."
    exit 1
fi

log_info "Consultando disponibilidad de Loki y una consulta de lectura..."
curl --fail --silent --show-error --max-time 10 \
    --get "${LOKI_URL%/}/loki/api/v1/query" \
    --data-urlencode 'query={job=~".+"}' \
    --output /dev/null
log_ok "Loki responde a consultas."

log_info "Comprobando que Restic abre el repositorio configurado..."
restic snapshots --json >/dev/null
log_ok "Restic pudo leer los metadatos del repositorio."

if [ -n "${NETDATA_URL:-}" ]; then
    log_info "Consultando disponibilidad de Netdata..."
    curl --fail --silent --show-error --max-time 10 \
        "${NETDATA_URL%/}/api/v1/info" \
        --output /dev/null
    log_ok "Netdata responde."
fi
