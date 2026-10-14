#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Script de Configuración del Cortafuegos UFW
# Ubicación: config/ufw/rules.sh
# ==============================================================================
# Este script aplica una política de "Default Deny" y habilita únicamente los
# puertos estrictamente indispensables para la operativa del servidor web y su
# administración segura.
# ==============================================================================

set -euo pipefail

# Colores para salida informativa
ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m' # Sin color

log_info() { echo -e "${AZUL}[INFO]${NC} $1"; }
log_ok() { echo -e "${VERDE}[OK]${NC} $1"; }
log_warn() { echo -e "${AMARILLO}[AVISO]${NC} $1"; }
log_err() { echo -e "${ROJO}[ERROR]${NC} $1" >&2; }

# 1. Comprobar privilegios de superusuario (root)
if [ "$(id -u)" -ne 0 ]; then
    log_err "Este script requiere privilegios de superusuario (root o sudo)."
    exit 1
fi

# 2. Comprobar que ufw está instalado
if ! command -v ufw >/dev/null 2>&1; then
    log_warn "UFW no está instalado. Instalándolo..."
    apt update && apt install -y ufw
fi

# 3. Detectar puerto SSH en ejecución (por defecto 22 o puerto personalizado)
SSH_PORT=$(ss -tulpn | grep -E 'sshd|ssh' | awk '{print $5}' | sed -e 's/.*://' | head -n 1)
SSH_PORT=${SSH_PORT:-22}
log_info "Puerto SSH detectado en el host: ${SSH_PORT}"

# Preguntar confirmación antes de aplicar
echo -e "${AMARILLO}======================================================================${NC}"
echo -e "  CONFIGURACIÓN DEL CORTAFUEGOS UFW - FACTORIO TECH SOLUTIONS"
echo -e "${AMARILLO}======================================================================${NC}"
echo -e "Se aplicarán las siguientes reglas:"
echo -e "  - Política por defecto: DENEGAR entrada, PERMITIR salida"
echo -e "  - Permitir SSH en puerto: ${SSH_PORT}/tcp (con límite de tasa)"
echo -e "  - Permitir HTTP (80/tcp) y HTTPS (443/tcp)"
echo -e "  - Registrar eventos a nivel: low"
echo -e "${AMARILLO}----------------------------------------------------------------------${NC}"

# 4. Restablecer reglas existentes (opcional con respaldo)
log_info "Creando copia de respaldo de la configuración actual de UFW..."
if [ -d /etc/ufw ]; then
    cp -r /etc/ufw "/etc/ufw.backup.$(date +%Y%m%d_%H%M%S)"
fi

# 5. Aplicar políticas por defecto
log_info "Estableciendo política por defecto (Default Deny Incoming)..."
ufw default deny incoming
ufw default allow outgoing
ufw default deny routed

# 6. Permitir SSH con limitación de tasa para prevenir ataques de fuerza bruta
log_info "Permitiendo SSH con rate limit en puerto ${SSH_PORT}/tcp..."
ufw limit "${SSH_PORT}/tcp" comment "SSH Hardened Access"

# Si el puerto estándar es distinto del detectado (ej. 2222), permitir también para evitar lockout
if [ "${SSH_PORT}" != "2222" ]; then
    log_info "Añadiendo permiso preventivo para puerto SSH alternativo 2222/tcp..."
    ufw limit 2222/tcp comment "SSH Alternative Hardened"
fi

# 7. Permitir servicios web Nginx
log_info "Permitiendo tráfico web HTTP (80/tcp) y HTTPS (443/tcp)..."
ufw allow 80/tcp comment "HTTP Web Ingress"
ufw allow 443/tcp comment "HTTPS Web Ingress"

# 8. Habilitar registro de eventos
log_info "Configurando nivel de logging del cortafuegos..."
ufw logging low

# 9. Activar UFW de forma no interactiva
log_info "Activando el cortafuegos..."
ufw --force enable

# 10. Mostrar resumen del estado resultante
echo ""
log_ok "Cortafuegos UFW configurado exitosamente."
ufw status verbose
