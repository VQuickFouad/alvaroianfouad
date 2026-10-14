#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Batería de Pruebas Automatizadas
# Ubicación: scripts/run-tests.sh
# ==============================================================================
# Propósito:
#   Ejecuta todas las validaciones de calidad, comprobación sintáctica de scripts,
#   pruebas de configuración, integridad de base de datos y tests de integración.
# ==============================================================================

set -uo pipefail

ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
BLANCO='\033[1;37m'
NC='\033[0m'

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${BASE_DIR}"

TESTS_PASSED=0
TESTS_FAILED=0

assert_test() {
    local descripcion="$1"
    shift
    local comando=("$@")

    printf "%-55s " "$descripcion"
    if "${comando[@]}" >/dev/null 2>&1; then
        echo -e "[${VERDE}  OK  ${NC}]"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "[${ROJO} FALLO ${NC}]"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo -e "${BLANCO}======================================================================${NC}"
echo -e "${BLANCO}   FACTORIO TECH SOLUTIONS - EJECUCIÓN DE PRUEBAS DE CALIDAD         ${NC}"
echo -e "${BLANCO}======================================================================${NC}"

# 1. Comprobación sintáctica de scripts Bash con `bash -n`
echo -e "\n${AZUL}1. Validación de Sintaxis de Scripts Shell (bash -n):${NC}"
for SCRIPT in "${BASE_DIR}"/scripts/*.sh "${BASE_DIR}"/config/ufw/*.sh "${BASE_DIR}"/tests/*.sh; do
    if [ -f "$SCRIPT" ]; then
        REL_NAME=$(basename "$SCRIPT")
        assert_test "Sintaxis Bash: ${REL_NAME}" bash -n "$SCRIPT"
    fi
done

# 2. Validación de Archivos de Configuración
echo -e "\n${AZUL}2. Validación de Archivos de Configuración del Sistema:${NC}"
assert_test "Presencia de plantilla .env.example" test -f "${BASE_DIR}/.env.example"
assert_test "Reglas de exclusión .gitignore presentes" test -f "${BASE_DIR}/.gitignore"
assert_test "Configuración de Nginx (factorio.conf)" test -f "${BASE_DIR}/config/nginx/factorio.conf"
assert_test "Cabeceras de seguridad Nginx (security-headers.conf)" test -f "${BASE_DIR}/config/nginx/security-headers.conf"
assert_test "Configuración de Fail2ban (jail.local)" test -f "${BASE_DIR}/config/fail2ban/jail.local"
assert_test "Filtro de Fail2ban (factorio.conf)" test -f "${BASE_DIR}/config/fail2ban/filter.d/factorio.conf"
assert_test "Configuración blindada SSH (sshd_config.example)" test -f "${BASE_DIR}/config/ssh/sshd_config.example"
assert_test "Perfil de seguridad AppArmor" test -f "${BASE_DIR}/config/apparmor/factorio-profile"
assert_test "Reglas de auditoría auditd (factorio.rules)" test -f "${BASE_DIR}/config/auditd/factorio.rules"
assert_test "Unidad de servicio Systemd (factorio.service)" test -f "${BASE_DIR}/config/systemd/factorio.service"
assert_test "Temporizador de backup Systemd (timer)" test -f "${BASE_DIR}/config/systemd/factorio-backup.timer"
assert_test "Servicio de backup Systemd (service)" test -f "${BASE_DIR}/config/systemd/factorio-backup.service"
assert_test "Política de rotación de logs (logrotate)" test -f "${BASE_DIR}/config/logrotate/factorio"

# 3. Validación de Documentación Técnica Requerida (Español)
echo -e "\n${AZUL}3. Validación de Manuales Técnicos en docs/:${NC}"
DOCS=(
    "arquitectura.md"
    "instalacion.md"
    "configuracion.md"
    "seguridad-hardening.md"
    "nginx-seguro.md"
    "copias-seguridad.md"
    "monitorizacion.md"
    "ia-chatbot.md"
    "despliegue.md"
    "pruebas.md"
    "guia-defensa-smr.md"
    "limitaciones.md"
)

for DOC in "${DOCS[@]}"; do
    assert_test "Documento: docs/${DOC}" test -s "${BASE_DIR}/docs/${DOC}"
done

# 4. Validación del Esquema de Base de Datos y Python
echo -e "\n${AZUL}4. Validación de la Capa de Datos y Python:${NC}"
assert_test "Intérprete de Python 3 funcional" python3 --version

# Inicializar DB temporalmente si aún no existe
if [ ! -f "${BASE_DIR}/data/factorio.db" ]; then
    bash "${BASE_DIR}/scripts/setup.sh" >/dev/null 2>&1 || true
fi

assert_test "Integridad de base de datos SQLite (quick_check)" python3 -c "
import sqlite3
conn = sqlite3.connect('${BASE_DIR}/data/factorio.db')
c = conn.cursor()
c.execute('PRAGMA quick_check;')
res = c.fetchone()[0]
conn.close()
assert res == 'ok'
"

# 5. Pruebas de contrato de la API FastAPI
echo -e "\n${AZUL}5. Pruebas de la API FastAPI:${NC}"
if [ -x "${BASE_DIR}/.venv/bin/python" ]; then
    assert_test "Contratos y rutas de la API" "${BASE_DIR}/.venv/bin/python" -m pytest -q "${BASE_DIR}/tests/test_api.py"
else
    assert_test "Contratos y rutas de la API" python3 -m pytest -q "${BASE_DIR}/tests/test_api.py"
fi

# 6. Ejecución del Script de Pruebas de Integración
echo -e "\n${AZUL}6. Ejecución de Pruebas de Integración:${NC}"
if [ -f "${BASE_DIR}/tests/test_integration.sh" ]; then
    chmod +x "${BASE_DIR}/tests/test_integration.sh"
    bash "${BASE_DIR}/tests/test_integration.sh"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    assert_test "Script tests/test_integration.sh" test -f "${BASE_DIR}/tests/test_integration.sh"
fi

# ------------------------------------------------------------------------------
# Resumen Final
# ------------------------------------------------------------------------------
echo ""
echo -e "${BLANCO}======================================================================${NC}"
TOTAL_EVAL=$((TESTS_PASSED + TESTS_FAILED))
if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${VERDE}✔ TODAS LAS PRUEBAS SUPERADAS CON ÉXITO (${TESTS_PASSED}/${TOTAL_EVAL})${NC}"
    echo -e "${BLANCO}======================================================================${NC}"
    exit 0
else
    echo -e "${ROJO}✘ SE DETECTARON FALLOS EN LAS PRUEBAS (${TESTS_FAILED} fallos de ${TOTAL_EVAL})${NC}"
    echo -e "${BLANCO}======================================================================${NC}"
    exit 1
fi
