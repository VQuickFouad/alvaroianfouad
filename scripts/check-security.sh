#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Auditoría Automatizada de Seguridad y Bastionado
# Ubicación: scripts/check-security.sh
# ==============================================================================
# Propósito:
#   Inspecciona la configuración del sistema operativo y evalúa más de 10
#   puntos críticos de control de seguridad (SSH, UFW, Fail2ban, sysctl,
#   AppArmor, permisos, etc.) calculando una puntuación global sobre 100.
# ==============================================================================

set -uo pipefail

# Colores para salida interactiva
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
CYAN='\033[0;36m'
BLANCO='\033[1;37m'
NC='\033[0m' # Sin color

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

CHECKS_PASSED=0
CHECKS_TOTAL=0

report_check() {
    local nombre="$1"
    local resultado="$2" # 0=PASS, 1=FAIL, 2=WARN
    local detalle="$3"
    local recomendacion="${4:-}"

    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))

    if [ "$resultado" -eq 0 ]; then
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
        printf "%-50s [%bPASS%b]\n" "$nombre" "$VERDE" "$NC"
        if [ -n "$detalle" ]; then
            echo -e "   ${AZUL}↳ Detalle:${NC} $detalle"
        fi
    elif [ "$resultado" -eq 2 ]; then
        CHECKS_PASSED=$((CHECKS_PASSED + 1)) # Parcial
        printf "%-50s [%bWARN%b]\n" "$nombre" "$AMARILLO" "$NC"
        if [ -n "$detalle" ]; then
            echo -e "   ${AMARILLO}↳ Aviso:${NC} $detalle"
        fi
        if [ -n "$recomendacion" ]; then
            echo -e "   ${CYAN}↳ Recomendación:${NC} $recomendacion"
        fi
    else
        printf "%-50s [%bFAIL%b]\n" "$nombre" "$ROJO" "$NC"
        if [ -n "$detalle" ]; then
            echo -e "   ${ROJO}↳ Fallo:${NC} $detalle"
        fi
        if [ -n "$recomendacion" ]; then
            echo -e "   ${CYAN}↳ Recomendación:${NC} $recomendacion"
        fi
    fi
}

echo -e "${BLANCO}======================================================================${NC}"
echo -e "${BLANCO}   FACTORIO TECH SOLUTIONS - AUDITORÍA DE SEGURIDAD DEL SERVIDOR     ${NC}"
echo -e "${BLANCO}======================================================================${NC}"
echo -e "Fecha: $(date '+%Y-%m-%d %H:%M:%S') | Host: $(hostname)"
echo "----------------------------------------------------------------------"

# ------------------------------------------------------------------------------
# 1. Comprobación de Permisos del Archivo .env
# ------------------------------------------------------------------------------
if [ -f "${BASE_DIR}/.env" ]; then
    ENV_PERM=$(stat -c "%a" "${BASE_DIR}/.env" 2>/dev/null || stat -f "%Lp" "${BASE_DIR}/.env" 2>/dev/null || echo "unknown")
    if [ "$ENV_PERM" = "600" ] || [ "$ENV_PERM" = "400" ]; then
        report_check "Permisos de archivo confidencial .env" 0 "Permisos restrictivos $ENV_PERM correctos."
    else
        report_check "Permisos de archivo confidencial .env" 1 "Permisos actuales: $ENV_PERM (inseguros)." "Ejecute: chmod 600 ${BASE_DIR}/.env"
    fi
else
    report_check "Permisos de archivo confidencial .env" 2 "Archivo .env no detectado en la raíz." "Copie .env.example como .env y restrinja permisos."
fi

# ------------------------------------------------------------------------------
# 2. Comprobación de Clave Secreta Criptográfica (SECRET_KEY)
# ------------------------------------------------------------------------------
if [ -f "${BASE_DIR}/.env" ]; then
    if grep -q "SECRET_KEY=cambiar-esta-clave-en-produccion" "${BASE_DIR}/.env" || grep -q "SECRET_KEY=\s*$" "${BASE_DIR}/.env"; then
        report_check "Fortaleza de SECRET_KEY en .env" 1 "Se detecta la clave por defecto o vacía." "Genere una clave única: openssl rand -hex 32 y asígnela a SECRET_KEY."
    else
        report_check "Fortaleza de SECRET_KEY en .env" 0 "Clave personalizada y no predeterminada."
    fi
else
    report_check "Fortaleza de SECRET_KEY en .env" 2 "No se pudo auditar SECRET_KEY (falta .env)."
fi

# ------------------------------------------------------------------------------
# 3. Comprobación de Configuración de OpenSSH
# ------------------------------------------------------------------------------
SSHD_CONFIG="/etc/ssh/sshd_config"
if [ -f "$SSHD_CONFIG" ]; then
    # Login de Root
    ROOT_LOGIN=$(grep -E "^PermitRootLogin" "$SSHD_CONFIG" | awk '{print $2}' || echo "yes")
    if [ "$ROOT_LOGIN" = "no" ]; then
        report_check "Acceso SSH: Prohibición de login root directo" 0 "PermitRootLogin configurado en 'no'."
    else
        report_check "Acceso SSH: Prohibición de login root directo" 1 "PermitRootLogin es '$ROOT_LOGIN'." "Configure 'PermitRootLogin no' en /etc/ssh/sshd_config."
    fi

    # Autenticación por Contraseña
    PASS_AUTH=$(grep -E "^PasswordAuthentication" "$SSHD_CONFIG" | awk '{print $2}' || echo "yes")
    if [ "$PASS_AUTH" = "no" ]; then
        report_check "Acceso SSH: Autenticación por contraseña desactivada" 0 "PasswordAuthentication en 'no' (solo llaves públicas)."
    else
        report_check "Acceso SSH: Autenticación por contraseña desactivada" 2 "PasswordAuthentication en '$PASS_AUTH'." "Recomendado: 'PasswordAuthentication no' tras verificar llaves."
    fi
else
    report_check "Acceso SSH: Archivo de configuración OpenSSH" 2 "sshd_config no encontrado (entorno de pruebas/contenedor)." "En host físico verifique /etc/ssh/sshd_config."
fi

# ------------------------------------------------------------------------------
# 4. Comprobación del Cortafuegos UFW
# ------------------------------------------------------------------------------
if command -v ufw >/dev/null 2>&1; then
    UFW_STATUS=$(ufw status 2>/dev/null | grep "Status:" | awk '{print $2}' || echo "inactive")
    if [ "$UFW_STATUS" = "active" ]; then
        report_check "Cortafuegos UFW: Estado de protección activo" 0 "UFW se encuentra activo y filtrando paquetes."
    else
        report_check "Cortafuegos UFW: Estado de protección activo" 1 "UFW está inactivo o deshabilitado." "Ejecute: sudo ./config/ufw/rules.sh"
    fi
else
    report_check "Cortafuegos UFW: Paquete instalado" 2 "UFW no está instalado en este entorno." "Instale ufw: sudo apt install ufw"
fi

# ------------------------------------------------------------------------------
# 5. Comprobación de Fail2ban
# ------------------------------------------------------------------------------
if command -v fail2ban-client >/dev/null 2>&1; then
    if systemctl is-active --quiet fail2ban 2>/dev/null; then
        JAILS=$(fail2ban-client status 2>/dev/null | grep "Jail list:" | sed 's/.*Jail list://' | tr -d '\t' || echo "ninguna")
        report_check "Prevención de Intrusiones: Fail2ban activo" 0 "Servicio activo. Cárceles: ${JAILS}"
    else
        report_check "Prevención de Intrusiones: Fail2ban activo" 1 "Fail2ban instalado pero servicio inactivo." "Inicie con: sudo systemctl enable --now fail2ban"
    fi
else
    report_check "Prevención de Intrusiones: Fail2ban instalado" 2 "Fail2ban no instalado." "Instale con: sudo apt install fail2ban"
fi

# ------------------------------------------------------------------------------
# 6. Comprobación de Parámetros de Red del Kernel (sysctl)
# ------------------------------------------------------------------------------
# SYN Cookies
SYN_COOKIES=$(cat /proc/sys/net/ipv4/tcp_syncookies 2>/dev/null || echo "0")
if [ "$SYN_COOKIES" = "1" ]; then
    report_check "Kernel Hardening: Protección SYN Cookies" 0 "Protección activa contra SYN Flood (tcp_syncookies=1)."
else
    report_check "Kernel Hardening: Protección SYN Cookies" 1 "SYN Cookies desactivado (tcp_syncookies=0)." "Añada 'net.ipv4.tcp_syncookies = 1' en /etc/sysctl.d/."
fi

# RP Filter (Reverse Path Filtering contra Spoofing)
RP_FILTER=$(cat /proc/sys/net/ipv4/conf/all/rp_filter 2>/dev/null || echo "0")
if [ "$RP_FILTER" = "1" ] || [ "$RP_FILTER" = "2" ]; then
    report_check "Kernel Hardening: Reverse Path Filtering (Spoofing)" 0 "Filtrado de ruta inversa activo (rp_filter=$RP_FILTER)."
else
    report_check "Kernel Hardening: Reverse Path Filtering (Spoofing)" 1 "Filtrado de ruta inversa inactivo." "Añada 'net.ipv4.conf.all.rp_filter = 1' en sysctl."
fi

# ASLR (Address Space Layout Randomization)
ASLR_VAL=$(cat /proc/sys/kernel/randomize_va_space 2>/dev/null || echo "0")
if [ "$ASLR_VAL" = "2" ]; then
    report_check "Kernel Hardening: ASLR Completo" 0 "Aleatorización de memoria completa (randomize_va_space=2)."
else
    report_check "Kernel Hardening: ASLR Completo" 1 "ASLR incompleto o desactivado (valor: $ASLR_VAL)." "Active con: sudo sysctl -w kernel.randomize_va_space=2"
fi

# ------------------------------------------------------------------------------
# 7. Comprobación de AppArmor / Módulo de Seguridad
# ------------------------------------------------------------------------------
if command -v aa-status >/dev/null 2>&1; then
    if aa-status --enabled 2>/dev/null; then
        report_check "Confinamiento de Procesos: AppArmor habilitado" 0 "AppArmor activo en el kernel."
    else
        report_check "Confinamiento de Procesos: AppArmor habilitado" 1 "AppArmor presente pero no habilitado en el arranque."
    fi
else
    report_check "Confinamiento de Procesos: AppArmor disponible" 2 "Herramientas de AppArmor no instaladas o kernel sin soporte."
fi

# ------------------------------------------------------------------------------
# 8. Comprobación de Permisos de Directorios de Datos
# ------------------------------------------------------------------------------
if [ -d "${BASE_DIR}/data" ]; then
    DATA_PERM=$(stat -c "%a" "${BASE_DIR}/data" 2>/dev/null || stat -f "%Lp" "${BASE_DIR}/data" 2>/dev/null || echo "unknown")
    if [ "$DATA_PERM" = "700" ] || [ "$DATA_PERM" = "750" ]; then
        report_check "Permisos del directorio de datos (data/)" 0 "Permisos correctos: $DATA_PERM."
    else
        report_check "Permisos del directorio de datos (data/)" 1 "Permisos permisivos: $DATA_PERM." "Ejecute: chmod 700 ${BASE_DIR}/data"
    fi
else
    report_check "Permisos del directorio de datos (data/)" 2 "Directorio data/ no encontrado." "Ejecute ./scripts/setup.sh"
fi

# ------------------------------------------------------------------------------
# 9. Cálculo y Presentación de la Puntuación Final
# ------------------------------------------------------------------------------
echo "----------------------------------------------------------------------"
if [ "$CHECKS_TOTAL" -gt 0 ]; then
    SCORE=$(( (CHECKS_PASSED * 100) / CHECKS_TOTAL ))
else
    SCORE=0
fi

echo -e "Pruebas Superadas: ${CHECKS_PASSED} de ${CHECKS_TOTAL}"

if [ "$SCORE" -ge 85 ]; then
    echo -e "Puntuación de Seguridad Global: ${VERDE}${SCORE}% [NIVEL ALTO / BASTIONADO ROBUSTO]${NC}"
elif [ "$SCORE" -ge 60 ]; then
    echo -e "Puntuación de Seguridad Global: ${AMARILLO}${SCORE}% [NIVEL MEDIO / REQUIERE ATENCIÓN]${NC}"
else
    echo -e "Puntuación de Seguridad Global: ${ROJO}${SCORE}% [NIVEL CRÍTICO / VULNERABLE]${NC}"
fi

echo -e "${BLANCO}======================================================================${NC}"

# Si se llama desde la aplicación, guardar en SQLite
if [ -f "${BASE_DIR}/data/factorio.db" ]; then
    python3 - <<EOF 2>/dev/null || true
import sqlite3
import json

try:
    conn = sqlite3.connect("${BASE_DIR}/data/factorio.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO security_audits (score, checks_passed, checks_total, report_json)
        VALUES (?, ?, ?, ?)
    """, (${SCORE}, ${CHECKS_PASSED}, ${CHECKS_TOTAL}, json.dumps({
        "score": ${SCORE},
        "passed": ${CHECKS_PASSED},
        "total": ${CHECKS_TOTAL},
        "status": "completed"
    })))
    conn.commit()
    conn.close()
except Exception:
    pass
EOF
fi

exit 0
