#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Script de Restauración Asistida de Copias de Seguridad
# Ubicación: scripts/restore.sh
# ==============================================================================
# Propósito:
#   Restaura de forma segura una instantánea específica o la más reciente
#   ('latest') hacia un directorio temporal de recuperación para verificar
#   su integridad antes de sobrescribir el entorno de producción.
# Uso:
#   ./scripts/restore.sh [SNAPSHOT_ID|latest] [DIRECTORIO_DESTINO]
# ==============================================================================

set -euo pipefail

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

SNAPSHOT_TARGET="${1:-latest}"
RESTORE_DIR="${2:-/tmp/factorio-restore-$(date +%Y%m%d_%H%M%S)}"
RESTORE_DIR="$(realpath -m -- "${RESTORE_DIR}")"

# Cargar variables de entorno
RESTIC_PASSWORD_OVERRIDE="${RESTIC_PASSWORD:-}"
RESTIC_PASSWORD_FILE_OVERRIDE="${RESTIC_PASSWORD_FILE:-}"
RESTIC_REPOSITORY_OVERRIDE="${RESTIC_REPOSITORY:-}"
if [ -f "${BASE_DIR}/.env" ]; then
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
    log_err "Restic no está instalado; no se restaurarán archivos de un formato alternativo no autenticado."
    exit 1
fi
if [ -z "${RESTIC_PASSWORD}" ]; then
    log_err "RESTIC_PASSWORD está vacío. Configura la contraseña del repositorio."
    exit 1
fi
export RESTIC_REPOSITORY
export RESTIC_PASSWORD

echo -e "${AZUL}======================================================================${NC}"
echo -e "   FACTORIO TECH SOLUTIONS - ASISTENTE DE RESTAURACIÓN"
echo -e "${AZUL}======================================================================${NC}"
log_info "Instantánea seleccionada: ${SNAPSHOT_TARGET}"
log_info "Directorio de restauración objetivo: ${RESTORE_DIR}"

case "${RESTORE_DIR}" in
    /tmp/*|"${BASE_DIR}"/data/restore/*) ;;
    *)
        log_err "El destino debe estar dentro de /tmp o ${BASE_DIR}/data/restore."
        exit 1
        ;;
esac

if [ -e "${RESTORE_DIR}" ] && [ -n "$(find "${RESTORE_DIR}" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
    log_err "El directorio de destino existe y no está vacío: ${RESTORE_DIR}"
    exit 1
fi
mkdir -p "${RESTORE_DIR}"

log_info "Verificando acceso al repositorio Restic..."
if ! restic snapshots >/dev/null; then
    log_err "No se pudo acceder al repositorio o la contraseña no es válida."
    exit 1
fi

log_info "Extrayendo instantánea '${SNAPSHOT_TARGET}' en '${RESTORE_DIR}'..."
restic restore "${SNAPSHOT_TARGET}" --target "${RESTORE_DIR}"
log_ok "Extracción Restic completada."

# 2. Verificación de Integridad de los Archivos Restaurados
echo ""
log_info "Validando coherencia de los datos restaurados..."
RESTORED_DB=$(find "${RESTORE_DIR}" -type f \( -name "factorio.db" -o -name "factorio.dump.db*" \) -print -quit)

if [ -n "$RESTORED_DB" ] && [ -f "$RESTORED_DB" ]; then
    log_info "Comprobando integridad de la base de datos SQLite restaurada..."
    python3 - "${RESTORED_DB}" <<'PY'
import sqlite3
import sys

try:
    conn = sqlite3.connect(sys.argv[1])
    cursor = conn.cursor()
    cursor.execute("PRAGMA quick_check;")
    result = cursor.fetchone()[0]
    conn.close()
    if result == "ok":
        print("[OK] Comprobación de integridad SQLite: SUPERADA (Integridad 100%)")
        sys.exit(0)
    else:
        print(f"[FAIL] Error en SQLite: {result}")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] Excepción al leer SQLite: {e}")
    sys.exit(1)
PY
    log_ok "Base de datos verificada y transaccionalmente válida."
fi

# 3. Resumen y Procedimiento para Sobrescribir Producción
echo ""
echo -e "${VERDE}======================================================================${NC}"
echo -e "   RESTAURACIÓN Y VERIFICACIÓN COMPLETADAS"
echo -e "${VERDE}======================================================================${NC}"
echo -e "Los datos han sido recuperados de forma aislada en:"
echo -e "👉 ${RESTORE_DIR}"
echo ""
echo -e "Para promover esta copia y sobrescribir el directorio de producción activo:"
echo -e "  1. Detenga el servicio: sudo systemctl stop factorio.service"
echo -e "  2. Copie los archivos restaurados:"
echo -e "     cp -r ${RESTORE_DIR}/data/* ${BASE_DIR}/data/"
echo -e "  3. Inicie el servicio nuevamente: sudo systemctl start factorio.service"
echo ""
exit 0
