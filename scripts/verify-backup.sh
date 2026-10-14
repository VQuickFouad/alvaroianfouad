#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Script de Verificación de Integridad de Copias
# Ubicación: scripts/verify-backup.sh
# ==============================================================================
# Propósito:
#   Audita el repositorio de copias de seguridad de Restic:
#   1. Comprueba la estructura interna del índice y los metadatos de instantáneas.
#   2. Verifica que no haya bloques corruptos (*bit rot*).
#   3. Muestra las estadísticas de instantáneas almacenadas y tamaño en disco.
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
    log_err "Restic no está instalado."
    exit 1
fi
if [ -z "${RESTIC_PASSWORD}" ]; then
    log_err "RESTIC_PASSWORD está vacío. Configura la contraseña del repositorio."
    exit 1
fi
export RESTIC_REPOSITORY
export RESTIC_PASSWORD

echo -e "${AZUL}======================================================================${NC}"
echo -e "   FACTORIO TECH SOLUTIONS - AUDITORÍA DE INTEGRIDAD DE BACKUP"
echo -e "${AZUL}======================================================================${NC}"
log_info "Verificando repositorio en: ${RESTIC_REPOSITORY}"

log_info "1. Comprobando estructura interna de metadatos (restic check)..."
restic check
log_ok "Estructura de metadatos e índices íntegra."

echo ""
log_info "2. Comprobando subconjunto de datos empaquetados (--read-data-subset=5%)..."
restic check --read-data-subset=5%
log_ok "Verificación de bloques de datos superada sin corrupción."

echo ""
log_info "3. Catálogo de Instantáneas Almacenadas:"
restic snapshots

echo ""
log_info "4. Estadísticas del Repositorio:"
restic stats --mode raw-data

echo ""
echo -e "${VERDE}======================================================================${NC}"
echo -e "   AUDITORÍA DE INTEGRIDAD DE RESPALDO FINALIZADA"
echo -e "${VERDE}======================================================================${NC}"
exit 0
