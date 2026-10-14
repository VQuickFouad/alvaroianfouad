# Guía Integral de Despliegue - Factorio Tech Solutions 🚀📦

Esta guía cubre todas las modalidades de despliegue para **Factorio Tech Solutions**: entorno de desarrollo local, puesta en producción empresarial nativa con **Systemd** y **Nginx**, y entorno de laboratorio autocontenido mediante **Docker Compose**.

---

## 1. Modalidades de Despliegue Disponibles

| Modalidad | Uso Recomendado | Requisitos | Complejidad |
| :--- | :--- | :--- | :--- |
| **1. Desarrollo Local** | Programación, pruebas unitarias y maquetación | Python 3.10+ | Mínima |
| **2. Producción Nativa (Systemd + Nginx)** | Despliegue en servidores reales de PYMEs (Bare-metal o VPS) | Ubuntu Server 22.04/24.04, Nginx, Restic | Media (Recomendada) |
| **3. Laboratorio Docker Compose** | Formación, demostraciones aisladas y pruebas de concepto | Docker Engine y Docker Compose | Baja |

---

## 2. Modalidad 1: Desarrollo Local Rápido

Para trabajar en el código o probar características en su estación de trabajo:

```bash
# 1. Preparar entorno y dependencias
chmod +x scripts/*.sh
./scripts/setup.sh

# 2. Configurar entorno básico
cp .env.example .env

# 3. Lanzar servidor de desarrollo
./scripts/start-dev.sh
```

El servidor quedará disponible en `http://localhost:8000`.

---

## 3. Modalidad 2: Despliegue en Producción (Systemd + Nginx)

Este método es el estándar recomendado para PYMEs con Ubuntu Server. Proporciona supervisión continua de procesos, rearranque automático tras caídas o reinicios del sistema, y aislamiento por usuario.

### 3.1. Estructura de Directorios y Permisos
```bash
# Crear directorio principal
sudo mkdir -p /opt/factorio
sudo useradd -r -s /bin/bash -d /opt/factorio -m factorio

# Clonar el proyecto en /opt/factorio/app
cd /opt/factorio
sudo -u factorio git clone https://github.com/factorio-tech/factorio-solutions.git app
cd /opt/factorio/app

# Crear carpetas requeridas
sudo -u factorio mkdir -p /opt/factorio/app/data /opt/factorio/app/logs
sudo chmod 700 /opt/factorio/app/data /opt/factorio/app/logs
```

### 3.2. Instalación de Dependencias en Entorno Virtual
```bash
sudo -u factorio python3 -m venv /opt/factorio/app/.venv
sudo -u factorio /opt/factorio/app/.venv/bin/pip install --upgrade pip
sudo -u factorio /opt/factorio/app/.venv/bin/pip install -r requirements.txt 2>/dev/null || true
```

### 3.3. Configuración de Variables de Entorno de Producción
```bash
sudo -u factorio cp .env.example .env
# Generar clave secreta segura
SECRET_GENERADA=$(openssl rand -hex 32)
sudo -u factorio sed -i "s/cambiar-esta-clave-en-produccion/$SECRET_GENERADA/" .env
sudo -u factorio sed -i "s/DEMO_MODE=true/DEMO_MODE=false/" .env
sudo -u factorio sed -i "s/DEBUG=true/DEBUG=false/" .env
sudo chmod 600 .env
```

### 3.4. Instalación de la Unidad de Servicio Systemd
Copie el archivo de servicio proporcionado en `config/systemd/factorio.service`:

```bash
sudo cp config/systemd/factorio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now factorio.service
```

Verifique que el servicio está activo y saludable:
```bash
sudo systemctl status factorio.service
```

### 3.5. Configuración de Nginx como Proxy Inverso y Terminador TLS
Copie la configuración de Nginx y las cabeceras de seguridad:

```bash
sudo cp config/nginx/security-headers.conf /etc/nginx/snippets/
sudo cp config/nginx/factorio.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/factorio.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Probar configuración y recargar
sudo nginx -t && sudo systemctl reload nginx
```

### 3.6. Emisión del Certificado SSL/TLS con Let's Encrypt
```bash
sudo certbot --nginx -d factorio.su-empresa.com
```

---

## 4. Modalidad 3: Producción Contenerizada con HTTPS

Esta variante publica únicamente Nginx en los puertos 80/443. La API queda
exclusivamente en la red interna de Compose; el contenedor de la aplicación corre
sin capabilities, con filesystem raíz de solo lectura y `SESSION_COOKIE_SECURE=true`.
Netdata y Loki deben configurarse como servicios externos accesibles desde el
contenedor, o se pueden dejar deshabilitados/no configurados.

1. Prepare los certificados emitidos para el dominio y colóquelos en
   `deploy/docker/certs/fullchain.pem` y `deploy/docker/certs/privkey.pem`.
   Proteja la clave privada y el directorio; no los añada a Git.
2. Copie `deploy/docker/.env.production.example` a
   `deploy/docker/.env.production`, configure el repositorio y las URLs de
   servicios disponibles. Genere el token de alta inicial y una contraseña larga
   para Restic como secretos separados. El
   ejemplo usa secretos Docker montados como archivos: cree `secrets/` y los tres
   ficheros indicados en el Compose (`auth_setup_token`, `restic_password` y
   `app_secret_key`), restrinja su lectura al UID 10001 (`factorio`) y proteja
   `.env.production` con `chmod 600`. No añada secretos a ese fichero ni a Git.
3. Edite `deploy/docker/nginx-production.conf` y sustituya
   `factorio.example.com` por el dominio cubierto por el certificado.
4. Valide y arranque la pila:

```bash
cd deploy/docker
docker compose -f docker-compose.production.yml config --quiet
docker compose -f docker-compose.production.yml up -d --build
```

La imagen incluye Restic. Use un repositorio remoto o almacenamiento separado
del volumen de datos de la aplicación. Configure `RESTIC_BACKUP_PATHS` como una
lista JSON de rutas dentro del contenedor que deben incluirse en la copia (el
ejemplo incluye `data/` y `config/`; no apunte el repositorio Restic dentro de
esas rutas). Inicialice el repositorio antes del primer backup:

```bash
docker compose -f docker-compose.production.yml exec factorio-app sh -c \
  'restic -r "$RESTIC_REPOSITORY" --password-file "$RESTIC_PASSWORD_FILE" init'
```

La configuración de Nginx
redirige HTTP a HTTPS; el certificado debe existir antes de iniciar el servicio.
La renovación del certificado se administra fuera de esta pila.

Tras arrancar, compruebe `https://<dominio>/api/health` y complete el alta
administrativa inicial. Nunca publique el puerto 8000 del contenedor. Las acciones
de control del host (por ejemplo reiniciar Nginx del host) no se habilitan por
ejecutar la app dentro del contenedor; para esas acciones, use el despliegue nativo
con permisos explícitos o manténgalas deshabilitadas.

Para probar desde una máquina que tenga acceso a Loki y Restic, cargue la
configuración operativa en el entorno de esa sesión y ejecute
`scripts/smoke-integrations.sh`. El script solo consulta una API de lectura de Loki
y lista metadatos de snapshots de Restic; no crea ni elimina copias. La integración
con IA se valida mediante el endpoint del panel y puede incurrir en costes cuando
se use un proveedor externo.

Con la variante Docker, ejecute la prueba dentro del contenedor de aplicación para
que los secretos Docker y las URLs configuradas estén disponibles:

```bash
docker compose -f docker-compose.production.yml exec factorio-app \
  /opt/factorio/app/scripts/smoke-integrations.sh
```

Ejemplo de preparación de los ficheros de secretos (genere y guarde cada salida
en un gestor de secretos protegido antes de continuar):

```bash
cd deploy/docker
install -d -m 700 secrets
openssl rand -hex 32 > secrets/auth_setup_token
openssl rand -hex 32 > secrets/restic_password
openssl rand -hex 32 > secrets/app_secret_key
sudo chown 10001:10001 secrets/auth_setup_token secrets/restic_password secrets/app_secret_key
chmod 400 secrets/auth_setup_token secrets/restic_password secrets/app_secret_key
cp .env.production.example .env.production
chmod 600 .env.production
```

Para OpenAI o Telegram, configure `AI_API_KEY_FILE` o
`TELEGRAM_BOT_TOKEN_FILE` y añada el secreto correspondiente al servicio
`factorio-app` del Compose antes de reiniciar. El backend soporta ambos formatos
`*_FILE` y solo reporta un error si el archivo indicado no puede leerse.

## 5. Modalidad 4: Laboratorio Contenerizado (Docker Compose)

El repositorio incluye una configuración completa en `deploy/docker/` que levanta la aplicación junto con toda la pila de observabilidad:
- **`factorio-app`:** El contenedor de la aplicación.
- **`nginx`:** Proxy inverso y terminador TLS.
- **`netdata`:** Telemetría de métricas del host y contenedores.
- **`loki`:** Servidor de agregación de logs.
- **`promtail`:** Recolector de logs de contenedores y sistema.

### 5.1. Despliegue del Laboratorio
```bash
cd deploy/docker

# Copiar configuración de entorno para Docker
cp .env.docker .env

# Levantar todos los servicios en segundo plano
docker compose up -d
```

### 5.2. Puertos Expuestos en el Laboratorio
| Servicio | Puerto Host | Descripción |
| :--- | :--- | :--- |
| **Nginx (HTTP)** | `8080` | Proxy de laboratorio sin TLS |
| **Factorio Directo** | No publicado | Disponible solo en la red interna |
| **Netdata Dashboard** | `19999` | Monitorización interactiva en tiempo real |
| **Grafana Loki** | `3100` | Endpoint de consulta de logs |

La variante de laboratorio no debe exponerse en redes no confiables. Para HTTPS,
utilice la modalidad de producción anterior.

### 5.3. Parada y Limpieza del Laboratorio
```bash
docker compose down
# Para eliminar volúmenes de datos:
docker compose down -v
```

---

## 6. Procedimientos de Actualización y Mantenimiento

Para actualizar Factorio a una nueva versión en un entorno de producción Systemd:

```bash
cd /opt/factorio/app
# 1. Obtener cambios del repositorio
sudo -u factorio git pull origin main

# 2. Actualizar dependencias de Python
sudo -u factorio /opt/factorio/app/.venv/bin/pip install --upgrade -r requirements.txt 2>/dev/null || true

# 3. Reiniciar el servicio de forma limpia
sudo systemctl restart factorio.service

# 4. Verificar estado y registros
sudo systemctl status factorio.service
sudo journalctl -u factorio.service -n 50 --no-pager
```
