# ==============================================================================
# Factorio Tech Solutions - Multi-Stage Dockerfile de Producción
# Ubicación: deploy/docker/Dockerfile
# ==============================================================================
# Características de Seguridad:
#   - Construcción multi-etapa para minimizar el tamaño de la imagen final.
#   - Usuario sin privilegios dedicado (factorio, UID 10001).
#   - Sin herramientas de compilación en la imagen de producción.
#   - Comprobación de salud nativa (HEALTHCHECK).
# ==============================================================================

# ------------------------------------------------------------------------------
# Etapa 1: Compilación y dependencias (Builder Stage)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Instalar dependencias de compilación del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear entorno virtual aislado
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Instalar y actualizar herramientas de empaquetado
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copiar manifiesto de dependencias si existe o instalar paquetes base
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir uvicorn fastapi; \
    fi

# ------------------------------------------------------------------------------
# Etapa 2: Imagen Final de Ejecución (Runtime Stage)
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL maintainer="Factorio Tech Solutions <devsecops@factorio.local>"
LABEL description="Factorio Tech Solutions Web Management & Security Engine"

# Instalar únicamente librerías de tiempo de ejecución estrictamente necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    restic \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario del sistema sin privilegios
RUN groupadd -g 10001 factorio && \
    useradd -u 10001 -g factorio -s /bin/false -d /opt/factorio -m factorio

# Copiar el entorno virtual preparado en la etapa 1
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/factorio/app

# Copiar código fuente y directorios necesarios
COPY --chown=factorio:factorio . .

# Asegurar directorios de datos y logs con permisos adecuados
RUN mkdir -p /opt/factorio/app/data /opt/factorio/app/logs && \
    chown -R factorio:factorio /opt/factorio && \
    chmod 700 /opt/factorio/app/data /opt/factorio/app/logs

# Cambiar al usuario no privilegiado
USER factorio

# Puerto expuesto por el servidor web interno
EXPOSE 8000

# Comprobación de salud continua del contenedor
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

# Comando de inicio predeterminado
CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
