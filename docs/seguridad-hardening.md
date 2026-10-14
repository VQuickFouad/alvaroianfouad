# Guía Integral de Bastionado de Servidores (Hardening) 🛡️

Esta guía describe el proceso de endurecimiento (*hardening*) de un servidor **Ubuntu Server (22.04 / 24.04 LTS)** para albergar servicios web de PYMEs de forma segura. Cada sección incluye:
- **Qué es** (Definición técnica)
- **Por qué** (Motivación y vector de ataque que mitiga)
- **Cómo** (Procedimiento exacto de configuración)
- **Verificación** (Comandos para comprobar la efectividad)
- **Reversión (Rollback)** (Pasos para deshacer el cambio si causa disrupción)

---

## 1. Instalación Mínima de Ubuntu Server

### Qué es
Instalación del sistema operativo utilizando la imagen oficial de Ubuntu Server seleccionando la opción *"Ubuntu Server (minimized)"*, prescindiendo de interfaces gráficas (X11/Wayland), compiladores por defecto y paquetes de ofimática o multimedia.

### Por qué
Reduce la superficie de ataque al mínimo estricto. Menos binarios y librerías en disco implican menos vulnerabilidades conocidas (CVEs) potenciales y un consumo de recursos sensiblemente inferior.

### Cómo
Durante el asistente de instalación de Ubuntu Server (Subiquity):
1. En la pantalla de selección de paquete base, elija **"Ubuntu Server (minimized)"**.
2. Desmarque la instalación de snaps adicionales en la pantalla final.

### Verificación
Comprobar el número total de paquetes instalados y la inexistencia de servidores X:
```bash
dpkg -l | wc -l
# En un sistema mínimo suele rondar entre 500 y 650 paquetes.
systemctl status display-manager.service
# Debe reportar 'Unit display-manager.service could not be found'.
```

### Reversión (Rollback)
No aplica directamente mediante rollback; si se requiere el conjunto estándar de utilidades de servidor, ejecute:
```bash
sudo unminimize
```

---

## 2. Actualizaciones del Sistema y Actualizaciones Desatendidas (`unattended-upgrades`)

### Qué es
Configuración de actualización automática y periódica de parches de seguridad del repositorio oficial de Ubuntu sin requerir intervención humana diaria.

### Por qué
La inmensa mayoría de intrusiones a servidores de PYMEs ocurren aprovechando vulnerabilidades públicas (N-Day) para las cuales ya existe parche disponible pero no fue aplicado a tiempo.

### Cómo
```bash
# 1. Instalar el paquete de actualizaciones desatendidas
sudo apt update && sudo apt install -y unattended-upgrades update-notifier-common

# 2. Habilitar el servicio desatendido
sudo dpkg-reconfigure -plow unattended-upgrades

# 3. Configurar la política en /etc/apt/apt.conf.d/50unattended-upgrades
sudo tee /etc/apt/apt.conf.d/50unattended-upgrades <<'EOF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Package-Blacklist {
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::InstallOnShutdown "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
EOF

# 4. Asegurar el intervalo de ejecución en /etc/apt/apt.conf.d/20auto-upgrades
sudo tee /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
```

### Verificación
Ejecutar un simulacro en modo prueba (*dry-run*):
```bash
sudo unattended-upgrades --dry-run --debug
```
Revisar el registro histórico de actualizaciones automáticas en:
```bash
tail -n 30 /var/log/unattended-upgrades/unattended-upgrades.log
```

### Reversión (Rollback)
Para deshabilitar las actualizaciones automáticas:
```bash
sudo dpkg-reconfigure -plow unattended-upgrades
# Seleccionar "No"
```

---

## 3. Gestión de Usuarios y Delegación `sudo`

### Qué es
Eliminación del uso directo de la cuenta de superusuario `root`, creación de usuarios administrativos nominativos con autenticación reforzada y limitación de permisos mediante `sudo`.

### Por qué
Previene el uso compartido de contraseñas de superusuario, garantiza la trazabilidad forense en los logs (`/var/log/auth.log`) de cada acción realizada y bloquea vectores de elevación de privilegios directos.

### Cómo
```bash
# 1. Crear un usuario de administración personal (ejemplo: 'sysadmin')
sudo adduser sysadmin

# 2. Agregar el usuario al grupo 'sudo'
sudo usermod -aG sudo sysadmin

# 3. Bloquear el acceso por contraseña a la cuenta root
sudo passwd -l root

# 4. Requerir contraseña para sudo y limitar tiempo de gracia de ticket a 5 minutos
echo 'Defaults timestamp_timeout=5' | sudo tee /etc/sudoers.d/timeout_hardening
sudo chmod 440 /etc/sudoers.d/timeout_hardening
```

### Verificación
Intentar iniciar sesión como root directamente:
```bash
su - root
# Debe devolver: "This account is currently not available" o fallo de autenticación.
```
Comprobar pertenencia al grupo sudo con el nuevo usuario:
```bash
id sysadmin
```

### Reversión (Rollback)
Si se necesita rehabilitar temporalmente la contraseña de root:
```bash
sudo passwd -u root
sudo rm -f /etc/sudoers.d/timeout_hardening
```

---

## 4. Endurecimiento de SSH (OpenSSH Server)

### Qué es
Blindaje del servicio OpenSSH mediante la prohibición de autenticación interactiva por contraseña, prohibición de login directo como `root`, restricción de usuarios admitidos y cambio opcional de puerto.

### Por qué
El puerto 22 es constantemente bombardeado por bots de fuerza bruta en internet. Obligar al uso de criptografía asimétrica (Ed25519 o RSA 4096) erradica por completo los ataques de diccionario y robo de credenciales débiles.

### Cómo
```bash
# 1. Respaldar la configuración original
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak

# 2. Copiar la clave pública del administrador en el servidor
# (Desde la máquina cliente: ssh-copy-id -i ~/.ssh/id_ed25519.pub sysadmin@ip-servidor)

# 3. Aplicar configuración segura en /etc/ssh/sshd_config.d/99-hardening.conf
sudo tee /etc/ssh/sshd_config.d/99-hardening.conf <<'EOF'
# Puerto no estándar para mitigar ruido de escáneres masivos
Port 2222
AddressFamily inet
Protocol 2

# Desactivar acceso directo a root y contraseñas
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
PubkeyAuthentication yes
AuthenticationMethods publickey

# Tiempos de espera y límites de intentos
LoginGraceTime 30
MaxAuthTries 3
MaxSessions 2

# Desactivación de túneles y reenvíos inseguros si no son necesarios
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no

# Restricción estricta de usuarios permitidos
AllowUsers sysadmin
EOF

# 4. Validar sintaxis ANTES de reiniciar el servicio
sudo sshd -t
if [ $? -eq 0 ]; then
    sudo systemctl restart ssh
fi
```

### Verificación
1. **NO CIERRE** su sesión SSH actual.
2. Abra una **nueva terminal** e intente conectarse con el puerto y la llave:
   ```bash
   ssh -p 2222 -i ~/.ssh/id_ed25519 sysadmin@ip-servidor
   ```
3. Intente conectarse con contraseña (debe ser rechazado inmediatamente con `Permission denied (publickey)`).

### Reversión (Rollback)
Si hay algún error antes de cerrar la sesión activa:
```bash
sudo rm -f /etc/ssh/sshd_config.d/99-hardening.conf
sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
sudo systemctl restart ssh
```

---

## 5. Configuración del Cortafuegos Perimetral (UFW)

### Qué es
Configuración de reglas de filtrado de paquetes a nivel de host mediante *Uncomplicated Firewall* (interfaz simplificada para `netfilter/iptables`).

### Por qué
Aplica una política de **denegación por defecto** (*Default Deny*), garantizando que solo los puertos deliberadamente autorizados puedan recibir tráfico desde el exterior.

### Cómo
```bash
# 1. Establecer directiva por defecto restrictiva
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 2. Autorizar el puerto SSH configurado (ejemplo: 2222 o 22 si no se modificó)
sudo ufw allow 2222/tcp comment 'SSH Port'

# 3. Autorizar tráfico web HTTP y HTTPS
sudo ufw allow 80/tcp comment 'HTTP (Certbot / Redirection)'
sudo ufw allow 443/tcp comment 'HTTPS Encrypted Web'

# 4. Habilitar el cortafuegos
sudo ufw --force enable
```

### Verificación
```bash
sudo ufw status verbose
```
Salida esperada:
```text
Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip

To                         Action      From
--                         ------      ----
2222/tcp                   ALLOW IN    Anywhere                   # SSH Port
80/tcp                     ALLOW IN    Anywhere                   # HTTP
443/tcp                    ALLOW IN    Anywhere                   # HTTPS
```

### Reversión (Rollback)
```bash
sudo ufw disable
```

---

## 6. Prevención de Intrusiones con Fail2ban

### Qué es
Demonio que monitoriza continuamente los archivos de registro (`auth.log`, `nginx/error.log`, etc.) y crea dinámicamente reglas en el cortafuegos para bloquear direcciones IP que exhiban patrones maliciosos repetidos.

### Por qué
Disuade y detiene ataques automatizados de fuerza bruta, escaneo de directorios vulnerables y peticiones abusivas.

### Cómo
```bash
# 1. Instalar fail2ban
sudo apt install -y fail2ban

# 2. Configurar la cárcel local en /etc/fail2ban/jail.local
sudo tee /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 4
banaction = ufw
ignoreip = 127.0.0.1/8 ::1

[sshd]
enabled = true
port    = 2222
logpath = %(sshd_log)s
backend = %(default_backend)s

[factorio-auth]
enabled = true
port    = 80,443
filter  = factorio
logpath = /opt/factorio/app/logs/factorio.log
maxretry = 5
bantime = 2h
EOF

# 3. Iniciar y habilitar el servicio
sudo systemctl enable --now fail2ban
```

### Verificación
Comprobar el estado general y las IPs bloqueadas:
```bash
sudo fail2ban-client status
sudo fail2ban-client status sshd
```

### Reversión (Rollback)
```bash
sudo systemctl stop fail2ban
sudo systemctl disable fail2ban
sudo ufw reload
```

---

## 7. Confinamiento de Procesos con AppArmor

### Qué es
Módulo de seguridad del Kernel Linux (LSM - Linux Security Module) que aplica control de acceso obligatorio (MAC), restringiendo los recursos, archivos y capacidades que cada binario puede ejecutar, independientemente del usuario que lo invoque.

### Por qué
Limita drásticamente el impacto si un servicio web sufre una vulnerabilidad de ejecución remota de código (RCE); el atacante no podrá leer archivos fuera de su directorio permitido ni invocar binarios del sistema no autorizados.

### Cómo
```bash
# 1. Asegurar que AppArmor está instalado y activo
sudo apt install -y apparmor apparmor-utils
sudo systemctl enable --now apparmor

# 2. Comprobar perfiles cargados
sudo aa-status
```

### Verificación
```bash
sudo aa-status | grep -E "profiles are in enforce mode"
```

### Reversión (Rollback)
Si un perfil entra en conflicto con una aplicación legítima, puede pasarse temporalmente a modo de queja (*complain mode*):
```bash
sudo aa-complain /usr/sbin/nginx
```

---

## 8. Auditoría del Sistema con `auditd`

### Qué es
Subsistema del kernel que audita llamadas al sistema, accesos a ficheros críticos y eventos de autenticación, escribiendo registros forenses detallados en `/var/log/audit/audit.log`.

### Por qué
Garantiza el no repudio y permite realizar análisis forense ante una intrusión para determinar con exactitud qué archivos fueron leídos o modificados y qué comandos se ejecutaron.

### Cómo
```bash
# 1. Instalar el paquete de auditoría
sudo apt install -y auditd audispd-plugins
sudo systemctl enable --now auditd

# 2. Configurar reglas de auditoría para archivos de configuración críticos
sudo tee /etc/audit/rules.d/factorio.rules <<'EOF'
# Auditar modificaciones en configuración de autenticación
-w /etc/passwd -p wa -k identity_changes
-w /etc/shadow -p wa -k identity_changes
-w /etc/group -p wa -k identity_changes
-w /etc/sudoers -p wa -k sudo_changes
-w /etc/sudoers.d/ -p wa -k sudo_changes

# Auditar ficheros de configuración de SSH
-w /etc/ssh/sshd_config -p wa -k sshd_config_changes
-w /etc/ssh/sshd_config.d/ -p wa -k sshd_config_changes

# Auditar directorio de Factorio Tech Solutions
-w /opt/factorio/app/.env -p wa -k factorio_env_access
EOF

# 3. Recargar reglas
sudo augenrules --load
```

### Verificación
Comprobar las reglas activas:
```bash
sudo auditctl -l
```
Buscar eventos generados con la clave de búsqueda:
```bash
sudo ausearch -k identity_changes -i
```

### Reversión (Rollback)
```bash
sudo rm -f /etc/audit/rules.d/factorio.rules
sudo augenrules --load
```

---

## 9. Evaluación Comparativa: CrowdSec vs. Fail2ban

En el diseño de la arquitectura para PYMEs evaluamos **Fail2ban** frente a **CrowdSec**:

| Criterio | Fail2ban | CrowdSec | Justificación de Elección |
| :--- | :--- | :--- | :--- |
| **Arquitectura** | Monolítico en Python, local | Modular en Go, desacoplado (Agente + LAPI) | Fail2ban viene preempaquetado en Ubuntu y tiene una huella en memoria casi nula (~20 MB). |
| **Inteligencia Colectiva** | Ninguna (solo reacciona a eventos locales) | Sí (alimentado por una base comunitaria global) | CrowdSec es excelente para flotas grandes, pero requiere conexión continua a servicios cloud externos y mayor sobrecarga de mantenimiento. |
| **Mantenimiento en PYME** | Muy sencillo, basado en expresiones regulares locales | Requiere gestión de colecciones, parsers y bouncers | Para el alcance de este proyecto, **Fail2ban** garantiza simplicidad y nula dependencia de terceros, manteniendo compatibilidad nativa con UFW. |

---

## 10. Evaluación: ModSecurity + OWASP CRS vs. Nginx Hardening

| Aspecto | ModSecurity + OWASP CRS | Nginx Hardened Nativo |
| :--- | :--- | :--- |
| **Consumo de Memoria** | Alto (requiere compilar o cargar módulo dinámico, ~80-150MB extra por worker) | Mínimo (nativo en C, < 15MB) |
| **Tasa de Falsos Positivos** | Frecuente si no se afinan exclusiones de reglas regex | Nula en configuración básica de headers y rate limit |
| **Protección** | Nivel aplicación profundo (SQLi, XSS, RFI) | L7 perímetro (Rate limit, DoS, headers, filtrado de métodos HTTP) |
| **Conclusión Técnica** | En entornos PYME con recursos limitados, el filtrado perimetral estricto de Nginx combinado con sanitización en el código backend de la aplicación proporciona el mejor equilibrio entre rendimiento y estabilidad operativa. |

---

## 11. Permisos del Sistema de Archivos y `umask`

### Qué es
Restricción de permisos de lectura, escritura y ejecución sobre directorios sensibles, y configuración de una máscara predeterminada restrictiva (`umask 027` o `077`).

### Por qué
Evita que archivos generados por servicios del sistema sean accesibles para usuarios sin privilegios locales (*Local Privilege Escalation* / *Information Leakage*).

### Cómo
```bash
# 1. Asegurar permisos restrictivos en /opt/factorio
sudo chown -R factorio:factorio /opt/factorio
sudo find /opt/factorio -type d -exec chmod 750 {} \;
sudo find /opt/factorio -type f -exec chmod 640 {} \;

# 2. Proteger archivo de variables y certificados
sudo chmod 600 /opt/factorio/app/.env

# 3. Configurar umask global en /etc/profile.d/umask.sh
echo "umask 027" | sudo tee /etc/profile.d/umask.sh
sudo chmod 644 /etc/profile.d/umask.sh
```

### Verificación
Comprobar permisos del archivo confidencial:
```bash
ls -la /opt/factorio/app/.env
# Debe mostrar: -rw------- 1 factorio factorio
```

### Reversión (Rollback)
```bash
sudo rm -f /etc/profile.d/umask.sh
```

---

## 12. Minimización de Servicios Innecesarios

### Qué es
Identificación y deshabilitación de servicios de red o demonios del sistema no requeridos para el rol de servidor web (ej. `bluetooth`, `cups`, `avahi-daemon`).

### Por qué
Cada servicio que escucha en un puerto o se ejecuta en segundo plano representa un proceso vulnerable susceptible de sufrir errores de corrupción de memoria o abusos de protocolo.

### Cómo
```bash
# Deshabilitar servicios irrelevantes en un servidor web
sudo systemctl stop avahi-daemon cups bluetooth 2>/dev/null || true
sudo systemctl disable avahi-daemon cups bluetooth 2>/dev/null || true
sudo systemctl mask avahi-daemon cups bluetooth 2>/dev/null || true
```

### Verificación
Verificar sockets de escucha abiertos:
```bash
sudo ss -tulpn
```
Solo deben figurar el puerto SSH, Nginx (80/443), la aplicación local (8000 en localhost) y los servicios de telemetría previstos.

### Reversión (Rollback)
```bash
sudo systemctl unmask avahi-daemon
sudo systemctl enable avahi-daemon
```

---

## 13. Endurecimiento del Kernel Linux (`sysctl`)

### Qué es
Ajuste de parámetros dinámicos del núcleo del sistema operativo en `/etc/sysctl.d/` para reforzar la pila de red TCP/IP y la memoria del sistema.

### Por qué
Mitiga ataques de suplantación de IP (IP Spoofing), previene ataques SYN Flood, deshabilita redirecciones ICMP maliciosas y activa la aleatorización del espacio de direcciones (ASLR).

### Cómo
```bash
sudo tee /etc/sysctl.d/99-factorio-security.conf <<'EOF'
# Mitigación de IP Spoofing (Reverse Path Filtering)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Desactivar redirecciones ICMP (previene ataques MITM de ruta)
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0

# Ignorar paquetes ping de difusión (evita ataques Smurf DoS)
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Protección contra ataques SYN Flood (SYN Cookies)
net.ipv4.tcp_syncookies = 1
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_synack_retries = 2

# Desactivar enrutamiento de paquetes IP (el servidor no actúa como router)
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# Desactivar Source Routing (evita enrutamiento arbitrario del atacante)
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0

# Registrar paquetes con direcciones sospechosas o marcianas
net.ipv4.conf.all.log_martians = 1

# ASLR Completo (Address Space Layout Randomization)
kernel.randomize_va_space = 2

# Restringir dmesg a usuarios con privilegios root
kernel.dmesg_restrict = 1

# Ocultar punteros del kernel para usuarios no privilegiados
kernel.kptr_restrict = 2
EOF

# Aplicar los cambios inmediatamente sin reiniciar
sudo sysctl --system
```

### Verificación
Comprobar que los parámetros se han aplicado:
```bash
sudo sysctl net.ipv4.tcp_syncookies
sudo sysctl kernel.randomize_va_space
# Debe retornar: net.ipv4.tcp_syncookies = 1 y kernel.randomize_va_space = 2
```

### Reversión (Rollback)
```bash
sudo rm -f /etc/sysctl.d/99-factorio-security.conf
sudo sysctl --system
```
