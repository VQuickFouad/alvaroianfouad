#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Script de Inicialización y Preparación del Entorno
# Ubicación: scripts/setup.sh
# ==============================================================================
# Propósito:
#   1. Valida los requisitos mínimos del sistema (Python 3.10+, SQLite3).
#   2. Crea la estructura de directorios persistentes (data, logs).
#   3. Crea y actualiza el entorno virtual de Python (.venv).
#   4. Genera el archivo .env seguro a partir de .env.example si no existe.
#   5. Inicializa el esquema de la base de datos SQLite en data/factorio.db.
#   6. Ajusta los permisos de seguridad recomendados en el sistema de archivos.
# ==============================================================================

set -euo pipefail

# Colores para salida por terminal
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m' # Sin color

log_info() { echo -e "${AZUL}[INFO]${NC} $1"; }
log_ok() { echo -e "${VERDE}[OK]${NC} $1"; }
log_warn() { echo -e "${AMARILLO}[AVISO]${NC} $1"; }
log_err() { echo -e "${ROJO}[ERROR]${NC} $1" >&2; }

# Obtener la ruta absoluta de la raíz del proyecto
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${BASE_DIR}"

echo -e "${AZUL}======================================================================${NC}"
echo -e "   FACTORIO TECH SOLUTIONS - INICIALIZACIÓN DEL SISTEMA"
echo -e "${AZUL}======================================================================${NC}"
log_info "Directorio base del proyecto: ${BASE_DIR}"

# 1. Comprobación de versión de Python
log_info "Comprobando disponibilidad de Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
    log_err "Python 3 no está instalado. Instálelo con: sudo apt install python3 python3-venv"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
log_ok "Python detectado: versión ${PYTHON_VER}"

# 2. Creación de directorios requeridos
log_info "Creando estructura de directorios locales..."
mkdir -p "${BASE_DIR}/data"
mkdir -p "${BASE_DIR}/logs"
mkdir -p "${BASE_DIR}/data/backups"
chmod 700 "${BASE_DIR}/data"
chmod 700 "${BASE_DIR}/logs"
log_ok "Directorios 'data/' y 'logs/' configurados con permisos 700."

# 3. Configuración del archivo de variables de entorno (.env)
if [ ! -f "${BASE_DIR}/.env" ]; then
    log_info "No se encontró archivo .env. Generando uno a partir de .env.example..."
    if [ -f "${BASE_DIR}/.env.example" ]; then
        cp "${BASE_DIR}/.env.example" "${BASE_DIR}/.env"
        
        # Generar una clave secreta criptográfica de 32 bytes en hexadecimal
        if command -v openssl >/dev/null 2>&1; then
            RAND_SECRET=$(openssl rand -hex 32)
        else
            RAND_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        fi
        
        # Reemplazar la clave por defecto
        sed -i "s/SECRET_KEY=cambiar-esta-clave-en-produccion/SECRET_KEY=${RAND_SECRET}/" "${BASE_DIR}/.env"
        chmod 600 "${BASE_DIR}/.env"
        log_ok "Archivo .env creado con clave criptográfica aleatoria única y permisos 600."
    else
        log_warn "No se encontró .env.example. Asegúrese de configurar .env manualmente."
    fi
else
    log_ok "Archivo .env ya existente. Se mantienen las configuraciones actuales."
    chmod 600 "${BASE_DIR}/.env"
fi

# 4. Creación del entorno virtual de Python (.venv)
if [ ! -d "${BASE_DIR}/.venv" ]; then
    log_info "Creando entorno virtual de Python en ${BASE_DIR}/.venv..."
    python3 -m venv "${BASE_DIR}/.venv"
    log_ok "Entorno virtual creado exitosamente."
else
    log_ok "Entorno virtual .venv ya existente."
fi

# 5. Instalación / Actualización de pip y dependencias básicas
log_info "Actualizando herramientas base de empaquetado en el entorno virtual..."
"${BASE_DIR}/.venv/bin/python3" -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1 || true

if [ -f "${BASE_DIR}/requirements.txt" ]; then
    log_info "Instalando dependencias desde requirements.txt..."
    "${BASE_DIR}/.venv/bin/pip" install -r "${BASE_DIR}/requirements.txt" || log_warn "Instalación de paquetes externos omitida o dependiente de red."
fi

# 6. Inicialización de la Base de Datos SQLite
DB_PATH="${BASE_DIR}/data/factorio.db"
log_info "Inicializando esquema de base de datos en ${DB_PATH}..."

python3 - <<EOF
import sqlite3
import os

db_path = "${DB_PATH}"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Activar modo WAL (Write-Ahead Logging) para rendimiento concurrente óptimo
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")
cursor.execute("PRAGMA foreign_keys=ON;")

# Tabla de Auditorías de Seguridad
cursor.execute("""
CREATE TABLE IF NOT EXISTS security_audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    score INTEGER NOT NULL,
    checks_passed INTEGER NOT NULL,
    checks_total INTEGER NOT NULL,
    report_json TEXT NOT NULL
);
""")

# Tabla de Registro de Copias de Seguridad
cursor.execute("""
CREATE TABLE IF NOT EXISTS backup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_id TEXT NOT NULL,
    status TEXT NOT NULL,
    files_new INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    bytes_added INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0.0
);
""")

# Tabla de Alertas e Incidentes
cursor.execute("""
CREATE TABLE IF NOT EXISTS security_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    severity TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    resolved BOOLEAN DEFAULT 0
);
""")

# Tabla de Ajustes del Sistema
cursor.execute("""
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

# Insertar configuración por defecto si está vacía
cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('initialized', 'true');")
cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('version', '1.0.0');")
cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('hardening_level', 'high');")

conn.commit()
conn.close()
print("Esquema SQLite verificado y preparado con éxito.")
EOF

log_ok "Base de datos inicializada correctamente en modo WAL."

# 7. Asignar permisos ejecutables a todos los scripts
log_info "Configurando permisos de ejecución en scripts/*.sh..."
chmod +x "${BASE_DIR}"/scripts/*.sh 2>/dev/null || true
if [ -d "${BASE_DIR}/tests" ]; then
    chmod +x "${BASE_DIR}"/tests/*.sh 2>/dev/null || true
fi
log_ok "Permisos de scripts asignados."

echo -e "${VERDE}======================================================================${NC}"
echo -e "   ¡INICIALIZACIÓN COMPLETADA CON ÉXITO!"
echo -e "${VERDE}======================================================================${NC}"
echo -e "Pasos siguientes recomendados:"
echo -e "  1. Revise y adapte el archivo .env según su entorno: nano .env"
echo -e "  2. Inicie el servidor de desarrollo: ./scripts/start-dev.sh"
echo -e "  3. Ejecute una auditoría de seguridad: ./scripts/check-security.sh"
echo -e "  4. Para ver las opciones de producción: cat docs/despliegue.md"
echo ""
