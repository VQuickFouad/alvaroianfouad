# Guía de Configuración - Factorio Tech Solutions ⚙️

Esta guía describe en detalle todas las opciones de configuración disponibles para **Factorio Tech Solutions**, estructuradas a través del archivo de variables de entorno `.env`.

---

## 1. Variables de Entorno del Sistema

El archivo `.env` se encuentra en la raíz del proyecto. Debe poseer permisos restringidos (`chmod 600 .env`) para evitar su lectura por usuarios no autorizados del sistema.

### 1.1. Configuración Básica de la Aplicación

| Variable | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | Cadena | `Factorio Tech Solutions` | Nombre formal que se muestra en el panel y las cabeceras. |
| `DEBUG` | Booleano | `false` | Activa mensajes de depuración detallados en logs y consola. En producción debe ser siempre `false`. |
| `DEMO_MODE` | Booleano | `true` | Si es `true`, simula respuestas de servicios no disponibles (Netdata, Loki, Restic) con datos sintéticos realistas. |
| `AUTH_SETUP_TOKEN` | Cadena | Vacío | Token de un solo uso lógico requerido para registrar la primera cuenta administradora. Genérelo aleatoriamente y consérvelo fuera del repositorio. |
| `AUTH_SETUP_TOKEN_FILE` | Ruta | Vacío | Alternativa para leer el token desde un archivo protegido; si se configura, tiene precedencia sobre `AUTH_SETUP_TOKEN`. |
| `SESSION_COOKIE_SECURE` | Booleano | `true` | Marca la cookie de sesión como Secure. Desactívelo únicamente en desarrollo HTTP local. |
| `SESSION_TTL_HOURS` | Entero | `8` | Caducidad de las sesiones de administrador. |
| `SECRET_KEY` | Cadena (Hex) | Generada por `setup.sh` | Se conserva para usos heredados; la sesión actual usa identificadores opacos aleatorios y no firma cookies con esta clave. |
| `SECRET_KEY_FILE` | Ruta | Vacío | Alternativa para leer `SECRET_KEY` desde un archivo protegido. |
| `DATABASE_URL` | URI | `sqlite:///./data/factorio.db` | Cadena de conexión. SQLite es la opción por defecto y recomendada. |
| `LOG_LEVEL` | Enum | `INFO` | Nivel mínimo de eventos a registrar (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `HOST` | IP | `0.0.0.0` | Dirección IP de escucha del servidor web interno. En producción detrás de Nginx puede limitarse a `127.0.0.1`. |
| `PORT` | Entero | `8000` | Puerto TCP de escucha de la aplicación interna. |

---

## 2. Modo Demostración vs. Modo Producción

### Alta y autenticación del administrador

1. Configure `AUTH_SETUP_TOKEN` en `.env` antes del primer arranque. Genere un valor
   aleatorio criptográfico (por ejemplo, `openssl rand -hex 32`) y proteja el archivo
   con `chmod 600 .env`.
2. Abra el panel y registre el usuario administrador mediante ese token y una
   contraseña de al menos 12 caracteres. El token de alta no se guarda en la base de
   datos; la contraseña se almacena como hash scrypt con sal aleatoria.
3. La API exige sesión en todas las rutas `/api/` excepto salud y autenticación.
   Las sesiones son opacas, expiran tras `SESSION_TTL_HOURS` y usan cookies
   `HttpOnly`, `SameSite=Strict` y token anti-CSRF para cambios.
4. Si la cuenta inicial ya fue creada, el token no permite crear otra. Para
   recuperación de cuenta, use un procedimiento local de administración de la base
   de datos; no existe un endpoint público de restablecimiento.

En desarrollo servido por HTTP local, establezca `SESSION_COOKIE_SECURE=false`.
En producción detrás de TLS manténgalo en `true`. La API no debe exponerse sin TLS
en redes no confiables.
`AI_API_KEY_FILE`, `RESTIC_PASSWORD_FILE` y `TELEGRAM_BOT_TOKEN_FILE` permiten
leer sus respectivos secretos desde archivos y tienen precedencia sobre la
variable de valor directo correspondiente.

### Modo Demostración (`DEMO_MODE=true`)
- **Propósito:** Ideal para entornos de laboratorio educativo (ciclos formativos SMR/ASIR), evaluaciones rápidas, pruebas de desarrollo local o máquinas donde aún no se han instalado daemons externos (Netdata, Loki, Restic).
- **Comportamiento:**
  - Las páginas usan datos explícitamente sintéticos identificados como demo.
  - La auditoría de seguridad reporta directivas simuladas sobre una plantilla segura.
  - Las decisiones de automatización son simuladas y no ejecutan comandos.

### Modo Producción (`DEMO_MODE=false`)
- **Propósito:** Despliegue en servidores reales de producción en PYMEs.
- **Comportamiento:**
  - Conecta directamente con las interfaces reales del sistema (`/proc/sys`, `ufw status`, `fail2ban-client`).
  - Lee métricas del host con psutil y audita UFW, Fail2ban y SSH mediante comandos de solo lectura.
  - Consulta Loki para los logs y Restic para snapshots; comunica con error explícito si las integraciones no están configuradas o disponibles.
  - Solo ejecuta acciones administrativas explícitamente permitidas y aprobadas; acciones no incluidas en el executor se rechazan.
  - Requiere que las variables de conexión apunten a instancias operativas.

### Preferencias de la interfaz

La página **Preferencias y configuración** guarda valores visibles del panel en
SQLite, pero no modifica automáticamente `.env`, las políticas del host ni los
parámetros activos de Loki, Restic, Netdata o los proveedores de IA. Configure
los valores operativos en `.env` y reinicie el backend cuando sea necesario.
Los secretos nunca se aceptan desde la API de preferencias.

---

## 3. Integración con Servicios de Monitorización y Registros

### 3.1. Netdata (Métricas del Sistema)
```env
NETDATA_URL=http://localhost:19999
METRICS_INTERVAL=30
```
- `NETDATA_URL`: URL base de la API de Netdata. Si se ejecuta en la misma máquina física, `http://localhost:19999` o `http://127.0.0.1:19999`. En Docker Compose, se utiliza `http://netdata:19999`.
- `METRICS_INTERVAL`: Intervalo en segundos con el que el backend consulta y agrega métricas históricas para refrescar la interfaz web.

### 3.2. Grafana Loki (Agregación de Logs)
```env
LOKI_URL=http://localhost:3100
LOG_RETENTION_DAYS=30
```
- `LOKI_URL`: Endpoint de ingesta y consulta de Loki. En local, `http://localhost:3100`. En Docker Compose, `http://loki:3100`.
- `LOG_RETENTION_DAYS`: Tiempo en días que la aplicación conserva los eventos antes de depurarlos de la base de datos interna.

El visor realiza consultas de lectura a `/loki/api/v1/query_range` para las últimas
24 horas. Si Loki no está disponible, el API responde `503`; no sustituye los logs
por eventos fabricados.

---

## 4. Configuración del Módulo de Inteligencia Artificial

Factorio Tech Solutions soporta tres modalidades para el asistente de soporte técnico y análisis de logs:

### 4.1. Opción 1: Deshabilitado / Simulado (`none`)
```env
AI_PROVIDER=none
AI_API_KEY=
AI_MODEL=
AI_BASE_URL=
```
- No realiza ninguna llamada externa. Devuelve recomendaciones heurísticas basadas en reglas de conocimiento local sin consumo de red ni costes de API.

### 4.2. Opción 2: Proveedor Local Privado (Ollama)
Recomendado para PYMEs con políticas estrictas de privacidad o cumplimiento del RGPD/GDPR:
```env
AI_PROVIDER=ollama
AI_API_KEY=
AI_MODEL=llama3.2
AI_BASE_URL=http://localhost:11434
```
- **Pasos para configurar Ollama en el servidor:**
  ```bash
  # Instalar Ollama en Linux
  curl -fsSL https://ollama.com/install.sh | sh
  
  # Descargar el modelo deseado (ejemplo: llama3.2 o mistral)
  ollama pull llama3.2
  ```

Las consultas se sanitizan antes de enviarse (claves privadas, tokens Bearer,
tokens tipo API, direcciones IP y correos). El contenido de los logs no se añade al
prompt automáticamente. En modo real con `AI_PROVIDER=none`, el endpoint devuelve
`503` en vez de una respuesta simulada.

### 4.3. Opción 3: OpenAI API
```env
AI_PROVIDER=openai
AI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
```
- **Nota de Seguridad:** Incluso utilizando OpenAI, el módulo de sanitización de Factorio anonimiza automáticamente IPs públicas, contraseñas, tokens y datos sensibles antes de transmitirlos.

---

## 5. Configuración del Bot de Notificaciones Telegram

El bot permite recibir avisos críticos (intentos reiterados de fuerza bruta, alertas de disco al 90%, fallos de backup) directamente en dispositivos móviles autorizados.

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_ALLOWED_USERS=987654321,112233445
```

### Pasos para Configurar el Bot de Telegram:
1. Abra Telegram y busque el usuario oficial `@BotFather`.
2. Envíe el comando `/newbot` y siga las instrucciones para asignarle un nombre y un alias.
3. Copie el token de acceso HTTP generado y asígnelo a `TELEGRAM_BOT_TOKEN`.
4. Para obtener su ID de usuario numérico:
   - Inicie una conversación con el bot `@userinfobot` en Telegram.
   - Copie el campo `Id` devuelto (ejemplo: `987654321`).
5. Asigne su ID a `TELEGRAM_ALLOWED_USERS`. Si hay varios administradores, sepárelos por coma sin espacios (`987654321,556677889`).
6. Cualquier mensaje proveniente de un ID no listado será automáticamente descartado y registrado como intento no autorizado en los logs de seguridad.

---

## 6. Configuración de Copias de Seguridad (Restic)

```env
RESTIC_REPOSITORY=/var/backups/factorio/repo
RESTIC_PASSWORD=ClaveUltraSeguraParaElRepositorioCifrado123!
```

En Docker Compose de producción se recomienda establecer
`RESTIC_PASSWORD_FILE=/run/secrets/restic_password` en lugar de incluir la clave
como variable de entorno.

- `RESTIC_REPOSITORY`: Puede ser una ruta en el sistema de archivos local (`/var/backups/factorio/repo`), un servidor SFTP (`sftp:usuario@servidor-remoto:/backups`) o un bucket compatible con Amazon S3 (`s3:s3.amazonaws.com/bucket-factorio`).
- `RESTIC_PASSWORD`: Clave de cifrado simétrico AES-256 utilizada para desbloquear el repositorio de Restic.
  - **ADVERTENCIA CRÍTICA:** Si pierde esta contraseña, los datos respaldados serán irrecuperables matemáticamente. Guárdela en un gestor de contraseñas seguro (como Bitwarden o KeePassXC).

Los scripts `backup.sh`, `verify-backup.sh` y `restore.sh` requieren Restic y una
contraseña configurada; no generan ni restauran archivos tar sin cifrar. Inicialice
el repositorio de Restic de forma explícita antes del primer backup. La restauración
se permite solo en un directorio vacío situado bajo `/tmp` o
`data/restore/`, para revisar los archivos antes de promoverlos manualmente.
