# Guía de Instalación - Factorio Tech Solutions 🚀

Este documento detalla el procedimiento paso a paso para desplegar **Factorio Tech Solutions** en un servidor Linux físico, máquina virtual o contenedor, enfocado principalmente en **Ubuntu Server 22.04 LTS / 24.04 LTS**.

---

## 1. Requisitos del Sistema

### Hardware Mínimo
- **CPU:** 1 núcleo x86_64 o ARM64 (2 núcleos recomendados).
- **Memoria RAM:** 1 GB (2 GB si se activan Netdata y Loki).
- **Almacenamiento:** 10 GB libres de disco duro o SSD.
- **Red:** Conexión a Internet para la descarga de paquetes y repositorios de seguridad.

### Software Base Necesario
- **Sistema Operativo:** Ubuntu Server 22.04 LTS o 24.04 LTS (o Debian 12).
- **Python:** Versión 3.10 o superior (Python 3.10, 3.11, 3.12, 3.13, 3.14).
- **Gestor de Paquetes:** `apt` y `pip`.
- **Servidor Web:** Nginx (para actuar como proxy inverso).
- **Herramienta de Backup:** Restic (paquete `restic`).

---

## 2. Preparación del Sistema Base

Antes de instalar dependencias específicas, asegúrese de que el sistema operativo está completamente actualizado y cuenta con las herramientas esenciales de administración:

```bash
# 1. Actualizar el índice de repositorios y paquetes instalados
sudo apt update && sudo apt upgrade -y

# 2. Instalar paquetes fundamentales del sistema
sudo apt install -y \
    curl \
    wget \
    git \
    ufw \
    fail2ban \
    restic \
    nginx \
    apparmor-utils \
    auditd \
    python3 \
    python3-pip \
    python3-venv \
    sqlite3
```

---

## 3. Creación del Usuario del Servicio

Por directrices de seguridad (Principio de Menor Privilegio), **nunca** ejecute la aplicación como usuario `root`. Se creará un usuario del sistema dedicado:

```bash
# Crear un usuario del sistema sin shell de login interactivo
sudo useradd -r -s /bin/bash -d /opt/factorio -m -c "Factorio Tech Solutions Daemon" factorio

# Asignar permisos al directorio de trabajo
sudo chmod 750 /opt/factorio
```

---

## 4. Clonación del Proyecto e Instalación de Dependencias

Descargue el código fuente en el directorio de trabajo:

```bash
# Clonar el repositorio
cd /opt/factorio
sudo -u factorio git clone https://github.com/factorio-tech/factorio-solutions.git app
cd /opt/factorio/app

# Otorgar permisos de ejecución a los scripts auxiliares
sudo -u factorio chmod +x scripts/*.sh
```

### Configuración del Entorno Virtual de Python
Aísle las librerías de Python en un entorno virtual (`venv`):

```bash
# Crear el entorno virtual con el usuario de la aplicación
sudo -u factorio python3 -m venv .venv

# Activar el entorno virtual e instalar las dependencias básicas
sudo -u factorio bash -c "source .venv/bin/activate && pip install --upgrade pip"
```

Alternativamente, puede ejecutar el script de instalación automatizado:
```bash
sudo -u factorio ./scripts/setup.sh
```

---

## 5. Configuración del Archivo `.env`

Copie la plantilla de variables de entorno y ajuste los parámetros críticos:

```bash
sudo -u factorio cp .env.example .env
sudo -u factorio chmod 600 .env
```

Edite el archivo `.env` con su editor preferido (`nano` o `vim`):
```bash
sudo -u factorio nano .env
```

Parámetros mínimos a verificar:
- `SECRET_KEY`: Genere una cadena aleatoria criptográfica:
  ```bash
  openssl rand -hex 32
  ```
  Pegue el valor resultante en la variable `SECRET_KEY`.
- `DEMO_MODE`: Ponga `false` en entornos de producción con servicios reales, o `true` en máquinas de desarrollo/laboratorio.
- `DATABASE_URL`: Ruta por defecto `sqlite:///./data/factorio.db`.

---

## 6. Inicialización de la Base de Datos y Directorios

Cree los directorios locales requeridos para datos persistentes, logs y copias de seguridad locales:

```bash
sudo -u factorio mkdir -p /opt/factorio/app/data
sudo -u factorio mkdir -p /opt/factorio/app/logs
sudo -u factorio chmod 700 /opt/factorio/app/data
sudo -u factorio chmod 700 /opt/factorio/app/logs
```

La base de datos SQLite se inicializa automáticamente al arrancar la aplicación por primera vez o ejecutando:

```bash
sudo -u factorio ./scripts/setup.sh
```

---

## 7. Primera Ejecución y Comprobación de Arranque

Para validar que la instalación se ha completado correctamente en modo manual:

```bash
cd /opt/factorio/app
sudo -u factorio ./scripts/start-dev.sh
```

Abra otra terminal o su navegador y realice una prueba de conectividad local:

```bash
curl -I http://127.0.0.1:8000/api/health
```

Respuesta esperada:
```http
HTTP/1.1 200 OK
content-type: application/json
```

Presione `Ctrl + C` en la terminal de la aplicación para detener el servidor de desarrollo. Para configurarlo como servicio permanente de inicio automático, consulte el manual [docs/despliegue.md](despliegue.md).
