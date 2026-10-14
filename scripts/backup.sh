#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Script de Copias de Seguridad Criptográficas
# Ubicación: scripts/backup.sh
# ==============================================================================
# Propósito:
#   1. Realiza un volcado seguro y atómico de la base de datos SQLite.
#   2. Cifra y deduplica los datos de producción en el repositorio Restic.
#   3. Aplica la política de retención y poda de instantáneas antiguas.
#   4. Registra el resultado en la base de datos de auditoría de Factorio.
# ==============================================================================

set -euo pipefail

# Colores informativos
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${AZUL}[INFO]${NC} $1"; }
log_ok() { echo -e "${VERDE}[OK]${NC} $1"; }
log_warn() { echo -e "${AMARILLO}[AVISO]${NC} $1"; }
log_err() { echo -e "${ROJO}[ERROR]${NC} $1" >&2; }

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${BASE_DIR}"

START_TIME=$(date +%s)
DATE_STR=$(date '+%Y-%m-%d %H:%M:%S')

# Cargar variables de entorno si existe .env
RESTIC_PASSWORD_OVERRIDE="${RESTIC_PASSWORD:-}"
RESTIC_PASSWORD_FILE_OVERRIDE="${RESTIC_PASSWORD_FILE:-}"
RESTIC_REPOSITORY_OVERRIDE="${RESTIC_REPOSITORY:-}"
if [ -f "${BASE_DIR}/.env" ]; then
    # Exportar variables sin sobrescribir las ya definidas en el entorno
    set -a
    # shellcheck disable=SC1091
    source "${BASE_DIR}/.env"
    set +a
fi

RESTIC_REPOSITORY="${RESTIC_REPOSITORY_OVERRIDE:-${RESTIC_REPOSITORY:-${BASE_DIR}/data/restic-repo}}"
RESTIC_PASSWORD="${RESTIC_PASSWORD_OVERRIDE:-${RESTIC_PASSWORD:-}}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE_OVERRIDE:-${RESTIC_PASSWORD_FILE:-}}"
if [ -n "${RESTIC_PASSWORD_FILE}" ]; then
    if [ ! -r "${RESTIC_PASSWORD_FILE}" ]; then
        log_err "No se puede leer RESTIC_PASSWORD_FILE."
        exit 1
    fi
    RESTIC_PASSWORD="$(<"${RESTIC_PASSWORD_FILE}")"
fi
if ! command -v restic >/dev/null 2>&1; then
    log_err "Restic no está instalado; no se creará un archivo tar sin cifrar."
    exit 1
fi
if [ -z "${RESTIC_PASSWORD}" ]; then
    log_err "RESTIC_PASSWORD está vacío. Configura una contraseña segura antes de continuar."
    exit 1
fi
export RESTIC_REPOSITORY
export RESTIC_PASSWORD

echo -e "${AZUL}======================================================================${NC}"
echo -e "   FACTORIO TECH SOLUTIONS - PROCESO DE COPIA DE SEGURIDAD"
echo -e "${AZUL}======================================================================${NC}"
log_info "Inicio de tarea de respaldo: ${DATE_STR}"
log_info "Repositorio de destino: ${RESTIC_REPOSITORY}"

# 1. Comprobación y volcado consistente de la base de datos SQLite
DB_FILE="${BASE_DIR}/data/factorio.db"
DUMP_FILE=""
cleanup() {
    if [ -n "${DUMP_FILE}" ] && [ -f "${DUMP_FILE}" ]; then
        rm -f -- "${DUMP_FILE}"
    fi
}
trap cleanup EXIT

log_info "Verificando acceso al repositorio Restic..."
if ! restic snapshots >/dev/null; then
    log_err "No se pudo abrir el repositorio. Verifica RESTIC_REPOSITORY, RESTIC_PASSWORD e inicializa el repositorio manualmente."
    exit 1
fi

if [ -f "$DB_FILE" ]; then
    DUMP_FILE="$(mktemp "${BASE_DIR}/data/factorio.dump.db.XXXXXX")"
    log_info "Generando volcado transaccional consistente de SQLite..."
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$DB_FILE" ".backup '${DUMP_FILE}'"
        log_ok "Volcado SQLite creado en ${DUMP_FILE}"
    else
        python3 - <<EOF
import sqlite3
source = sqlite3.connect("${DB_FILE}")
dest = sqlite3.connect("${DUMP_FILE}")
source.backup(dest)
dest.close()
source.close()
print("Volcado generado mediante Python sqlite3.")
EOF
        log_ok "Volcado SQLite generado con éxito."
    fi
fi

# 2. Ejecución del backup cifrado con Restic
SNAPSHOT_ID=""
BYTES_ADDED=0

log_info "Creando instantánea cifrada con Restic..."
if RESTIC_OUT=$(restic backup \
    --exclude="${BASE_DIR}/.venv" \
    --exclude="${BASE_DIR}/__pycache__" \
    --exclude="${BASE_DIR}/logs/*.log" \
    --exclude="${BASE_DIR}/.git" \
    --exclude="${RESTIC_REPOSITORY}" \
    --tag "factorio-core" \
    --tag "scheduled" \
    --json \
    "${BASE_DIR}/data" "${BASE_DIR}/config" "${BASE_DIR}/.env"); then
    read -r SNAPSHOT_ID BYTES_ADDED < <(
        printf '%s\n' "${RESTIC_OUT}" | python3 -c '
import json
import sys
for line in sys.stdin:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        continue
    if event.get("message_type") == "summary":
        print(event.get("snapshot_id", ""), event.get("data_added", 0))
'
    )
else
    log_err "La operación restic backup falló; no se registrará como exitosa."
    exit 1
fi

if [ -z "${SNAPSHOT_ID}" ]; then
    log_err "Restic terminó, pero no se pudo recuperar un ID de snapshot."
    exit 1
fi
log_ok "Instantánea cifrada completada con ID: ${SNAPSHOT_ID}"

if restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune --quiet; then
    log_ok "Política de retención aplicada."
else
    log_warn "El snapshot se creó, pero falló la poda/retención. Revisa el repositorio."
fi

# 3. Limpieza de archivos temporales de volcado
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# 4. Registro en la base de datos SQLite de auditoría
if [ -f "$DB_FILE" ]; then
    python3 - "${DB_FILE}" "${SNAPSHOT_ID}" "${BYTES_ADDED}" "${DURATION}" "${RESTIC_REPOSITORY}" <<'PY'
import sqlite3
import sys
import uuid

db_path, snapshot_id, bytes_added, duration, repository = sys.argv[1:]
with sqlite3.connect(db_path) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backup_records (
            id TEXT PRIMARY KEY,
            snapshot_id TEXT,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            size_bytes INTEGER NOT NULL DEFAULT 0,
            file_count INTEGER NOT NULL DEFAULT 0,
            repository TEXT NOT NULL,
            duration_seconds REAL NOT NULL DEFAULT 0,
            error_message TEXT,
            source TEXT NOT NULL DEFAULT 'real'
        )
    """)
    conn.execute("""
        INSERT INTO backup_records
            (id, snapshot_id, status, size_bytes, repository, duration_seconds, source)
        VALUES (?, ?, 'success', ?, ?, ?, 'real')
    """, (str(uuid.uuid4()), snapshot_id, int(bytes_added), repository, float(duration)))
    legacy_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='backup_history'"
    ).fetchone()
    if legacy_table:
        conn.execute("""
            INSERT INTO backup_history
                (snapshot_id, status, files_new, files_changed, bytes_added, duration_seconds)
            VALUES (?, 'SUCCESS', 0, 0, ?, ?)
        """, (snapshot_id, int(bytes_added), float(duration)))
PY
fi

echo -e "${VERDE}======================================================================${NC}"
echo -e "   ¡COPIA DE SEGURIDAD FINALIZADA CON ÉXITO! (Duración: ${DURATION}s)"
echo -e "${VERDE}======================================================================${NC}"
exit 0
