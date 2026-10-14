#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Asistente Interactivo de Bastionado del Sistema
# Ubicación: scripts/hardening.sh
# ==============================================================================
# Propósito:
#   Aplica de manera guiada e interactiva las directivas de seguridad recomendadas
#   para Ubuntu Server. Solicita confirmación explícita antes de cada cambio
#   crítico para evitar disrupciones accidentales o bloqueos de acceso (lockout).
# ==============================================================================

set -uo pipefail

ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
CYAN='\033[0;36m'
BLANCO='\033[1;37m'
NC='\033[0m'

log_info() { echo -e "${AZUL}[INFO]${NC} $1"; }
log_ok() { echo -e "${VERDE}[OK]${NC} $1"; }
log_warn() { echo -e "${AMARILLO}[AVISO]${NC} $1"; }
log_err() { echo -e "${ROJO}[ERROR]${NC} $1" >&2; }

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Comprobar privilegios de root
if [ "$(id -u)" -ne 0 ]; then
    log_err "Este script de bastionado requiere privilegios de superusuario (root o sudo)."
    echo "Ejecute: sudo $0"
    exit 1
fi

AUTO_YES=false
if [ "${1:-}" = "--yes" ] || [ "${1:-}" = "-y" ] || [ "${1:-}" = "--all" ]; then
    AUTO_YES=true
fi

ask_confirmation() {
    local prompt="$1"
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi
    echo -e -n "${AMARILLO}[?] ${prompt} [s/N]: ${NC}"
    read -r respuesta
    case "$respuesta" in
        [sS][iI]|[sS]) return 0 ;;
        *) return 1 ;;
    esac
}

echo -e "${BLANCO}======================================================================${NC}"
echo -e "${BLANCO}   FACTORIO TECH SOLUTIONS - ASISTENTE INTERACTIVO DE BASTIONADO     ${NC}"
echo -e "${BLANCO}======================================================================${NC}"
echo -e "Este asistente reforzará la seguridad de su servidor Ubuntu paso a paso."
echo -e "Antes de cada cambio se le solicitará confirmación."
echo ""

# ------------------------------------------------------------------------------
# Módulo 1: Actualizaciones del Sistema y Parches Desatendidos
# ------------------------------------------------------------------------------
echo -e "${CYAN}--- [Paso 1/7] Actualizaciones y Parches Automáticos ---${NC}"
if ask_confirmation "¿Desea configurar 'unattended-upgrades' para parches de seguridad automáticos?"; then
    log_info "Instalando y configurando actualizaciones desatendidas..."
    apt update && apt install -y unattended-upgrades update-notifier-common
    
    # Copiar configuración predefinida
    cat <<'EOF' > /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
    log_ok "Actualizaciones desatendidas configuradas correctamente."
else
    log_info "Paso omitido por el usuario."
fi

# ------------------------------------------------------------------------------
# Módulo 2: Endurecimiento de Parámetros del Kernel (sysctl)
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- [Paso 2/7] Parámetros de Red y Seguridad del Kernel (sysctl) ---${NC}"
if ask_confirmation "¿Desea aplicar la configuración blindada de red y memoria (sysctl)?"; then
    log_info "Aplicando parámetros de mitigación de IP spoofing, SYN flood y ASLR..."
    SYSCTL_CONF="/etc/sysctl.d/99-factorio-security.conf"
    cat <<'EOF' > "$SYSCTL_CONF"
# Factorio Tech Solutions - Kernel Hardening
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.ip_forward = 0
net.ipv4.conf.all.accept_source_route = 0
kernel.randomize_va_space = 2
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
EOF
    sysctl --system >/dev/null 2>&1 || sysctl -p "$SYSCTL_CONF"
    log_ok "Parámetros sysctl aplicados sin necesidad de reinicio."
else
    log_info "Paso omitido por el usuario."
fi

# ------------------------------------------------------------------------------
# Módulo 3: Cortafuegos UFW
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- [Paso 3/7] Cortafuegos UFW (Default Deny) ---${NC}"
if ask_confirmation "¿Desea ejecutar el script de configuración segura del cortafuegos UFW?"; then
    if [ -f "${BASE_DIR}/config/ufw/rules.sh" ]; then
        log_info "Ejecutando config/ufw/rules.sh..."
        bash "${BASE_DIR}/config/ufw/rules.sh"
    else
        log_warn "Script config/ufw/rules.sh no encontrado. Aplicando reglas básicas..."
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp comment 'SSH'
        ufw allow 80/tcp comment 'HTTP'
        ufw allow 443/tcp comment 'HTTPS'
        ufw --force enable
    fi
    log_ok "Cortafuegos UFW activo."
else
    log_info "Paso omitido por el usuario."
fi

# ------------------------------------------------------------------------------
# Módulo 4: Endurecimiento de OpenSSH Server
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- [Paso 4/7] Endurecimiento del Servidor SSH ---${NC}"
echo -e "${AMARILLO}¡ATENCIÓN! Asegúrese de contar con llaves públicas SSH autorizadas antes de desactivar contraseñas.${NC}"
if ask_confirmation "¿Desea blindar la configuración de OpenSSH (prohibir login root y password)?"; then
    SSHD_FILE="/etc/ssh/sshd_config"
    if [ -f "$SSHD_FILE" ]; then
        cp "$SSHD_FILE" "/etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Copia de respaldo de sshd_config generada."

        # Aplicar mediante directivas en sshd_config.d si está soportado
        if [ -d "/etc/ssh/sshd_config.d" ]; then
            cat <<'EOF' > /etc/ssh/sshd_config.d/99-factorio-hardening.conf
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
PubkeyAuthentication yes
MaxAuthTries 3
X11Forwarding no
EOF
        else
            sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' "$SSHD_FILE"
            sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_FILE"
        fi

        # Validar sintaxis antes de reiniciar
        if sshd -t; then
            systemctl restart ssh || systemctl restart sshd
            log_ok "OpenSSH endurecido y reiniciado con éxito."
            echo -e "${AMARILLO}NOTA: No cierre su sesión SSH actual hasta verificar la conexión en una nueva terminal.${NC}"
        else
            log_err "Error de sintaxis en sshd_config. Revertiendo cambios..."
            rm -f /etc/ssh/sshd_config.d/99-factorio-hardening.conf 2>/dev/null || true
        fi
    else
        log_warn "No se encontró el archivo /etc/ssh/sshd_config en este sistema."
    fi
else
    log_info "Paso omitido por el usuario."
fi

# ------------------------------------------------------------------------------
# Módulo 5: Instalación y Configuración de Fail2ban
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- [Paso 5/7] Prevención de Intrusiones con Fail2ban ---${NC}"
if ask_confirmation "¿Desea instalar y habilitar las cárceles de Fail2ban?"; then
    log_info "Instalando y configurando Fail2ban..."
    apt install -y fail2ban
    if [ -f "${BASE_DIR}/config/fail2ban/jail.local" ]; then
        cp "${BASE_DIR}/config/fail2ban/jail.local" /etc/fail2ban/jail.local
    fi
    if [ -f "${BASE_DIR}/config/fail2ban/filter.d/factorio.conf" ]; then
        mkdir -p /etc/fail2ban/filter.d
        cp "${BASE_DIR}/config/fail2ban/filter.d/factorio.conf" /etc/fail2ban/filter.d/factorio.conf
    fi
    systemctl enable --now fail2ban
    log_ok "Fail2ban configurado y activo."
else
    log_info "Paso omitido por el usuario."
fi

# ------------------------------------------------------------------------------
# Módulo 6: Permisos del Sistema de Archivos
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- [Paso 6/7] Permisos de Seguridad en Archivos de Factorio ---${NC}"
if ask_confirmation "¿Desea restringir permisos en los archivos confidenciales de la aplicación?"; then
    if [ -f "${BASE_DIR}/.env" ]; then
        chmod 600 "${BASE_DIR}/.env"
        log_ok "Permisos de .env cambiados a 600 (solo lectura/escritura propietario)."
    fi
    if [ -d "${BASE_DIR}/data" ]; then
        chmod 700 "${BASE_DIR}/data"
        log_ok "Permisos de data/ cambiados a 700."
    fi
    if [ -d "${BASE_DIR}/logs" ]; then
        chmod 700 "${BASE_DIR}/logs"
        log_ok "Permisos de logs/ cambiados a 700."
    fi
else
    log_info "Paso omitido por el usuario."
fi

# ------------------------------------------------------------------------------
# Módulo 7: Desactivación de Servicios Innecesarios
# ------------------------------------------------------------------------------
echo ""
echo -e "${CYAN}--- [Paso 7/7] Desactivación de Servicios Innecesarios ---${NC}"
if ask_confirmation "¿Desea deshabilitar servicios innecesarios (bluetooth, cups, avahi)?"; then
    log_info "Deteniendo y deshabilitando daemons no requeridos..."
    systemctl disable --now cups avahi-daemon bluetooth 2>/dev/null || true
    log_ok "Servicios no indispensables deshabilitados."
else
    log_info "Paso omitido por el usuario."
fi

echo ""
echo -e "${VERDE}======================================================================${NC}"
echo -e "   ¡BASTIONADO COMPLETADO CON ÉXITO!"
echo -e "${VERDE}======================================================================${NC}"
echo -e "Ejecute ahora la auditoría para verificar la puntuación obtenida:"
echo -e "👉 ${BASE_DIR}/scripts/check-security.sh"
echo ""
exit 0
