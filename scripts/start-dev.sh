#!/usr/bin/env bash
# ==============================================================================
# Factorio Tech Solutions - Servidor de Desarrollo Local
# Ubicación: scripts/start-dev.sh
# ==============================================================================
# Propósito:
#   Inicia el servidor en modo desarrollo con recarga en caliente o servidor
#   integrado ligero para pruebas y comprobaciones de laboratorio.
# ==============================================================================

set -euo pipefail

ROJO='\033[0;31m'
VERDE='\033[0;32m'
AMARILLO='\033[1;33m'
AZUL='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${AZUL}[INFO]${NC} $1"; }
log_ok() { echo -e "${VERDE}[OK]${NC} $1"; }
log_warn() { echo -e "${AMARILLO}[AVISO]${NC} $1"; }
log_err() { echo -e "${ROJO}[ERROR]${NC} $1" >&2; }

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${BASE_DIR}"

# 1. Asegurar configuración de entorno
if [ ! -f "${BASE_DIR}/.env" ]; then
    log_warn "No se encontró .env. Creándolo desde .env.example..."
    cp "${BASE_DIR}/.env.example" "${BASE_DIR}/.env"
fi

# Cargar variables de entorno
set -a
# shellcheck disable=SC1091
source "${BASE_DIR}/.env"
set +a

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

# Determinar intérprete de Python a utilizar
if [ -f "${BASE_DIR}/.venv/bin/python3" ]; then
    PYTHON_BIN="${BASE_DIR}/.venv/bin/python3"
else
    PYTHON_BIN="python3"
fi

echo -e "${AZUL}======================================================================${NC}"
echo -e "   FACTORIO TECH SOLUTIONS - SERVIDOR DE DESARROLLO"
echo -e "${AZUL}======================================================================${NC}"
log_info "Host: ${HOST}"
log_info "Puerto: ${PORT}"
log_info "Modo Demo: ${DEMO_MODE:-true}"
log_info "Intérprete Python: ${PYTHON_BIN}"
echo "----------------------------------------------------------------------"
echo -e "Presione ${AMARILLO}Ctrl + C${NC} para detener el servidor."
echo ""

# Comprobar si existe aplicación FastAPI / Uvicorn o ejecutar servidor reactivo Python
if [ -f "${BASE_DIR}/app/main.py" ] && "$PYTHON_BIN" -c "import uvicorn" 2>/dev/null; then
    log_info "Iniciando servidor Uvicorn con recarga en caliente..."
    exec "$PYTHON_BIN" -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
else
    log_info "Iniciando servidor de desarrollo integrado de Factorio..."
    exec "$PYTHON_BIN" - <<EOF
import http.server
import socketserver
import json
import os
import sys
from datetime import datetime

HOST = "${HOST}"
PORT = int("${PORT}")
BASE_DIR = "${BASE_DIR}"

class FactorioDevHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def _send_html(self, status_code, html_content):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def do_GET(self):
        # Endpoints de API REST
        if self.path in ('/api/health', '/health'):
            self._send_json(200, {
                "status": "healthy",
                "app": "Factorio Tech Solutions",
                "version": "1.0.0",
                "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true",
                "timestamp": datetime.now().isoformat()
            })
            return

        elif self.path == '/api/status':
            self._send_json(200, {
                "server": {
                    "hostname": os.uname().nodename,
                    "os": os.uname().sysname,
                    "release": os.uname().release,
                    "status": "running"
                },
                "security": {
                    "ufw": "active",
                    "fail2ban": "active",
                    "ssh_hardened": True,
                    "hardening_score": 92
                },
                "backup": {
                    "last_backup": datetime.now().strftime("%Y-%m-%d 02:30:00"),
                    "status": "verified",
                    "encryption": "AES-256-GCM"
                }
            })
            return

        elif self.path == '/api/metrics':
            self._send_json(200, {
                "cpu_percent": 14.5,
                "memory_percent": 42.1,
                "disk_percent": 35.8,
                "active_connections": 12,
                "metrics_source": "Factorio Telemetry Core"
            })
            return

        # Dashboard Web Principal
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Factorio Tech Solutions - Panel de Control</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card: #1e293b;
            --text: #f8fafc;
            --accent: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--border);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .header h1 {{ margin: 0; font-size: 1.6rem; color: var(--accent); }}
        .badge {{
            background: #064e3b;
            color: var(--success);
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: bold;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 1.15rem;
            color: #94a3b8;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }}
        .metric {{
            font-size: 2.2rem;
            font-weight: bold;
            color: var(--text);
            margin: 10px 0;
        }}
        .metric-sub {{ color: #94a3b8; font-size: 0.9rem; }}
        .links a {{
            color: var(--accent);
            text-decoration: none;
            display: inline-block;
            margin-right: 12px;
            margin-top: 8px;
        }}
        .links a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🛡️ Factorio Tech Solutions</h1>
            <div style="color: #94a3b8; font-size: 0.9rem; margin-top: 4px;">
                Plataforma de Gestión, Bastionado y Monitorización de Servidores Linux
            </div>
        </div>
        <div>
            <span class="badge">SISTEMA OPERATIVO</span>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Postura de Seguridad</h2>
            <div class="metric" style="color: var(--success);">92%</div>
            <div class="metric-sub">Puntuación de Bastionado (CIS Benchmark)</div>
            <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 12px;">
                • Cortafuegos UFW: Activo<br>
                • Fail2ban: Activo (3 cárceles)<br>
                • OpenSSH: Llave pública exclusiva
            </p>
        </div>

        <div class="card">
            <h2>Telemetría del Servidor</h2>
            <div class="metric">14.5% <span style="font-size: 1rem; color: #94a3b8;">CPU</span></div>
            <div class="metric-sub">RAM: 42.1% | Disco: 35.8% libre</div>
            <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 12px;">
                • Agente Netdata: En línea<br>
                • Loki Log Ingestion: Conectado<br>
                • Conexiones Activas: 12 sockets
            </p>
        </div>

        <div class="card">
            <h2>Copias de Seguridad</h2>
            <div class="metric" style="color: var(--accent);">Restic</div>
            <div class="metric-sub">Cifrado AES-256-GCM (Regla 3-2-1)</div>
            <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 12px;">
                • Último snapshot: Hoy 02:30 AM<br>
                • Integridad: Verificada (100% OK)<br>
                • Deduplicación: 4.8x ratio
            </p>
        </div>
    </div>

    <div class="card" style="margin-top: 24px;">
        <h2>Endpoints de la API y Documentación</h2>
        <div class="links">
            <a href="/api/health" target="_blank">▸ /api/health (Salud)</a>
            <a href="/api/status" target="_blank">▸ /api/status (Estado del Host)</a>
            <a href="/api/metrics" target="_blank">▸ /api/metrics (Métricas)</a>
        </div>
    </div>
</body>
</html>
"""
        self._send_html(200, html)

class ThreadingSimpleServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

server = ThreadingSimpleServer((HOST, PORT), FactorioDevHandler)
log_ok(f"Servidor escuchando en http://{HOST}:{PORT}")
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\n[INFO] Servidor detenido de forma ordenada.")
    sys.exit(0)
EOF
fi
