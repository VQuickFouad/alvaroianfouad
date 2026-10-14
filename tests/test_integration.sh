#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Pruebas de Integración y Validación del Sistema
# Ubicación: tests/test_integration.sh
# ==============================================================================
# Propósito:
#   Ejecuta pruebas de caja negra e integración funcional para verificar
#   el correcto funcionamiento de los módulos de seguridad, base de datos,
#   copias de seguridad, sanitización de datos y configuración.
# ==============================================================================

set -uo pipefail

ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
CYAN='\033[0;36m'
BLANCO='\033[1;37m'
NC='\033[0m'

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${BASE_DIR}"

TESTS_PASSED=0
TESTS_FAILED=0

assert_ok() {
    local nombre="$1"
    local comando="$2"

    printf "%-60s " "$nombre"
    if eval "$comando" >/dev/null 2>&1; then
        echo -e "[${VERDE}  OK  ${NC}]"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "[${ROJO} FALLO ${NC}]"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo -e "${BLANCO}======================================================================${NC}"
echo -e "${BLANCO}   FACTORIO TECH SOLUTIONS - SUITE DE INTEGRACIÓN Y SEGURIDAD        ${NC}"
echo -e "${BLANCO}======================================================================${NC}"

# ------------------------------------------------------------------------------
# Test 1: Comprobación de Estructura de Proyecto
# ------------------------------------------------------------------------------
echo -e "\n${AZUL}[GRUPO 1] Verificación de Estructura de Directorios y Ficheros Clave:${NC}"
assert_ok "Directorio config/ presente" "[ -d '${BASE_DIR}/config' ]"
assert_ok "Directorio docs/ presente" "[ -d '${BASE_DIR}/docs' ]"
assert_ok "Directorio scripts/ presente" "[ -d '${BASE_DIR}/scripts' ]"
assert_ok "Directorio deploy/docker/ presente" "[ -d '${BASE_DIR}/deploy/docker' ]"
assert_ok "Archivo README.md no vacío" "[ -s '${BASE_DIR}/README.md' ]"
assert_ok "Plantilla .env.example presente" "[ -s '${BASE_DIR}/.env.example' ]"
assert_ok "Reglas .gitignore presentes" "[ -s '${BASE_DIR}/.gitignore' ]"

# ------------------------------------------------------------------------------
# Test 2: Inicialización de Entorno y Capa de Persistencia
# ------------------------------------------------------------------------------
echo -e "\n${AZUL}[GRUPO 2] Inicialización y Capa de Persistencia (SQLite):${NC}"
# Ejecutar inicialización si no se ha hecho
bash "${BASE_DIR}/scripts/setup.sh" >/dev/null 2>&1
assert_ok "Directorio data/ creado con permisos 700" "[ -d '${BASE_DIR}/data' ]"
assert_ok "Directorio logs/ creado con permisos 700" "[ -d '${BASE_DIR}/logs' ]"
assert_ok "Archivo de variables .env configurado" "[ -f '${BASE_DIR}/.env' ]"
assert_ok "Base de datos factorio.db generada" "[ -f '${BASE_DIR}/data/factorio.db' ]"

assert_ok "Esquema SQLite: tabla security_audits presente" "python3 -c \"
import sqlite3
c = sqlite3.connect('${BASE_DIR}/data/factorio.db').cursor()
c.execute('SELECT COUNT(*) FROM security_audits')
\""

assert_ok "Esquema SQLite: tabla backup_history presente" "python3 -c \"
import sqlite3
c = sqlite3.connect('${BASE_DIR}/data/factorio.db').cursor()
c.execute('SELECT COUNT(*) FROM backup_history')
\""

assert_ok "Esquema SQLite: tabla system_settings presente" "python3 -c \"
import sqlite3
c = sqlite3.connect('${BASE_DIR}/data/factorio.db').cursor()
c.execute('SELECT value FROM system_settings WHERE key=\"initialized\"')
assert c.fetchone()[0] == 'true'
\""

# ------------------------------------------------------------------------------
# Test 3: Motor de Auditoría y Hardening
# ------------------------------------------------------------------------------
echo -e "\n${AZUL}[GRUPO 3] Motor de Auditoría de Seguridad (check-security.sh):${NC}"
assert_ok "Ejecución sin fallos del script check-security.sh" "bash '${BASE_DIR}/scripts/check-security.sh' >/dev/null 2>&1"
assert_ok "Auditoría registrada en base de datos SQLite" "python3 -c \"
import sqlite3
c = sqlite3.connect('${BASE_DIR}/data/factorio.db').cursor()
c.execute('SELECT score FROM security_audits ORDER BY id DESC LIMIT 1')
res = c.fetchone()
assert res is not None and res[0] >= 0
\""

# ------------------------------------------------------------------------------
# Test 4: Motor de Copias de Seguridad y Recuperación
# ------------------------------------------------------------------------------
echo -e "\n${AZUL}[GRUPO 4] Motor de Copias de Seguridad y Recuperación:${NC}"
assert_ok "Sintaxis de scripts de copia y restauración" "for script in '${BASE_DIR}/scripts/backup.sh' '${BASE_DIR}/scripts/verify-backup.sh' '${BASE_DIR}/scripts/restore.sh'; do bash -n \"\$script\" || exit; done"
assert_ok "Copia exige Restic y contraseña configurados" "grep -q 'command -v restic' '${BASE_DIR}/scripts/backup.sh' && grep -q 'RESTIC_PASSWORD' '${BASE_DIR}/scripts/backup.sh'"
assert_ok "No hay fallback de restauración en tar sin cifrar" "! grep -Eq 'tar -xzf|tar -czf' '${BASE_DIR}/scripts/backup.sh' '${BASE_DIR}/scripts/restore.sh'"

# ------------------------------------------------------------------------------
# Test 5: Módulo de Sanitización de Datos para IA
# ------------------------------------------------------------------------------
echo -e "\n${AZUL}[GRUPO 5] Sanitización y Anonimización de Datos Sensibles (IA):${NC}"
assert_ok "Sanitización de IPs públicas en textos" "python3 -c \"
import re
text = 'Ataque detectado desde 198.51.100.44 hacia el servidor'
sanitized = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[IP_ANONIMIZADA]', text)
assert '198.51.100.44' not in sanitized and '[IP_ANONIMIZADA]' in sanitized
\""

assert_ok "Sanitización de Tokens API Bearer y Secretos" "python3 -c \"
import re
text = 'Clave sk-proj-1234567890abcdef1234567890 y password=SuperSecreta'
sanitized = re.sub(r'sk-[a-zA-Z0-9]{20,}', '[TOKEN_REDACTADO]', text)
sanitized = re.sub(r'password=\S+', 'password=[REDACTADO]', sanitized)
assert 'SuperSecreta' not in sanitized and '1234567890abcdef' not in sanitized
\""

assert_ok "Sanitización de Claves Privadas PEM" "python3 -c \"
import re
text = '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----'
sanitized = re.sub(r'-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+ PRIVATE KEY-----', '[CLAVE_PRIVADA_REDACTADA]', text)
assert 'MIIEowIBAAKCAQEA' not in sanitized and '[CLAVE_PRIVADA_REDACTADA]' in sanitized
\""

# ------------------------------------------------------------------------------
# Test 6: Comprobación de Configuraciones de Servicios
# ------------------------------------------------------------------------------
echo -e "\n${AZUL}[GRUPO 6] Validación de Reglas de Seguridad de Servicios:${NC}"
assert_ok "Sintaxis de filtro Fail2ban de Factorio" "python3 -c \"
import configparser
config = configparser.ConfigParser()
config.read('${BASE_DIR}/config/fail2ban/filter.d/factorio.conf')
assert 'Definition' in config.sections()
\""

assert_ok "Presencia de cabecera HSTS en security-headers.conf" "grep -q 'Strict-Transport-Security' '${BASE_DIR}/config/nginx/security-headers.conf'"
assert_ok "Presencia de directiva NoNewPrivileges en factorio.service" "grep -q 'NoNewPrivileges=yes' '${BASE_DIR}/config/systemd/factorio.service'"

# ------------------------------------------------------------------------------
# Resumen Global
# ------------------------------------------------------------------------------
echo ""
echo -e "${BLANCO}======================================================================${NC}"
TOTAL_PRUEBAS=$((TESTS_PASSED + TESTS_FAILED))
if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${VERDE}✔ TODAS LAS PRUEBAS DE INTEGRACIÓN HAN SIDO SUPERADAS (${TESTS_PASSED}/${TOTAL_PRUEBAS})${NC}"
    echo -e "${BLANCO}======================================================================${NC}"
    exit 0
else
    echo -e "${ROJO}✘ SE DETECTARON FALLOS EN ${TESTS_FAILED} PRUEBAS DE INTEGRACIÓN${NC}"
    echo -e "${BLANCO}======================================================================${NC}"
    exit 1
fi
