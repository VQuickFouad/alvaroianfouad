# Guía de Bastionado y Configuración Segura de Nginx 🌐🔒

Esta guía describe cómo desplegar, afinar y asegurar **Nginx** como proxy inverso de alto rendimiento para **Factorio Tech Solutions**, protegiendo la aplicación frente a ataques web habituales y optimizando los recursos del sistema.

---

## 1. Instalación y Verificación Base

Instale la versión estable de Nginx desde los repositorios oficiales de Ubuntu:

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Habilitar el inicio automático y arrancar el servicio
sudo systemctl enable --now nginx
```

Verifique la versión instalada y la ausencia de errores en la configuración predeterminada:
```bash
nginx -v
sudo nginx -t
```

---

## 2. Afinación de Rendimiento y Conexiones (`nginx.conf`)

En servidores de PYMEs, es fundamental evitar el agotamiento de descriptores de archivos (*file descriptors*) y limitar el uso excesivo de buffers que pueda derivar en ataques de denegación de servicio (*Slowloris* o desbordamientos de búfer).

Ajuste `/etc/nginx/nginx.conf`:

```nginx
user www-data;
# Ajusta automáticamente el número de workers a la cantidad de núcleos CPU
worker_processes auto;
# Aumenta el límite de descriptores de archivo por proceso
worker_rlimit_nofile 65535;

pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    # Número máximo de conexiones simultáneas por worker
    worker_connections 2048;
    # Acepta tantas conexiones como sea posible por ciclo
    multi_accept on;
    use epoll;
}

http {
    ##
    # Ocultación de Información del Servidor
    ##
    # Oculta la versión exacta de Nginx en cabeceras de respuesta y páginas de error
    server_tokens off;

    ##
    # Optimización de Transferencia de Archivos
    ##
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;

    # Tiempos de espera estrictos para mitigar conexiones zombis y ataques Slowloris
    keepalive_timeout 30;
    client_body_timeout 15;
    client_header_timeout 15;
    send_timeout 15;

    # Tamaños de búfer seguros para prevenir ataques de desbordamiento
    client_body_buffer_size 128k;
    client_max_body_size 16M; # Ajustar si la aplicación admite subida de archivos
    client_header_buffer_size 1k;
    large_client_header_buffers 4 8k;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ##
    # Zonas de Limitación de Tasa (Rate Limiting)
    ##
    # 1. Zona general para mitigar DoS/escáneres: 20 req/s por IP
    limit_req_zone $binary_remote_addr zone=general_limit:10m rate=20r/s;
    # 2. Zona estricta para endpoints de login y API sensible: 5 req/s por IP
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/s;

    # Código de retorno cuando se excede la tasa (HTTP 429 Too Many Requests)
    limit_req_status 429;

    ##
    # Configuración de Registros Seguros
    ##
    log_format factorio_combined '$remote_addr - $remote_user [$time_local] '
                                 '"$request" $status $body_bytes_sent '
                                 '"$http_referer" "$http_user_agent" '
                                 'rt=$request_time uct="$upstream_connect_time" uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log factorio_combined;
    error_log /var/log/nginx/error.log warn;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
```

---

## 3. Cabeceras de Seguridad HTTP (`security-headers.conf`)

Cree el archivo `/etc/nginx/snippets/security-headers.conf` con las directivas recomendadas por OWASP:

```nginx
# 1. HTTP Strict Transport Security (HSTS)
# Obliga a los navegadores a conectarse solo mediante HTTPS durante 1 año
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# 2. X-Frame-Options
# Previene ataques de Clickjacking impidiendo que la web sea embebida en un <iframe>
add_header X-Frame-Options "DENY" always;

# 3. X-Content-Type-Options
# Evita la interpretación errónea de tipos MIME (MIME-type sniffing)
add_header X-Content-Type-Options "nosniff" always;

# 4. Referrer-Policy
# Protege la privacidad evitando enviar la URL completa en peticiones externas
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# 5. Permissions-Policy
# Deshabilita el acceso del navegador a periféricos sensibles no necesarios
add_header Permissions-Policy "geolocation=(), camera=(), microphone=(), payment=()" always;

# 6. Content Security Policy (CSP)
# Restringe de dónde pueden cargarse scripts, estilos e imágenes
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none';" always;
```

---

## 4. Configuración del Bloque de Servidor (`factorio.conf`)

Cree el archivo de configuración del sitio en `/etc/nginx/sites-available/factorio.conf`:

```nginx
# Redirección automática de HTTP a HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name factorio.empresa.local; # Reemplace por su FQDN o IP

    # Endpoint para validación de certificados Let's Encrypt / Certbot
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    # Redireccionar el resto del tráfico a HTTPS con código permanente 301
    location / {
        return 301 https://$host$request_uri;
    }
}

# Servidor Principal HTTPS
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name factorio.empresa.local;

    # Certificados TLS (Let's Encrypt o Certificado Autofirmado de Laboratorio)
    ssl_certificate /etc/ssl/certs/factorio-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/factorio-selfsigned.key;

    # Protocolos TLS modernos (TLS 1.2 y TLS 1.3 únicamente)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Parámetros de sesión SSL para optimizar latencia
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # Parámetros Diffie-Hellman seguros
    # Generar con: openssl dhparam -out /etc/nginx/dhparam.pem 2048
    ssl_dhparam /etc/nginx/dhparam.pem;

    # Inclusión de cabeceras de seguridad
    include /etc/nginx/snippets/security-headers.conf;

    # Bloqueo de acceso a archivos ocultos (.git, .env, .htaccess)
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Limitación de peticiones en endpoints de autenticación
    location /api/auth/ {
        limit_req zone=login_limit burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Proxy inverso principal hacia Factorio Backend
    location / {
        limit_req zone=general_limit burst=20 nodelay;

        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # Cabeceras requeridas para WebSockets y Proxy inverso
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Tiempos de espera con el backend
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }
}
```

---

## 5. Obtención y Renovación de Certificados TLS con Certbot

En entornos de producción con dominio público:

```bash
# Obtener y configurar certificado automáticamente
sudo certbot --nginx -d factorio.su-empresa.com

# Probar la renovación automática
sudo certbot renew --dry-run
```

Para entornos de laboratorio local o pruebas privadas sin dominio público, se genera un certificado autofirmado seguro:

```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/factorio-selfsigned.key \
  -out /etc/ssl/certs/factorio-selfsigned.crt \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=Factorio Tech Solutions/OU=DevSecOps/CN=factorio.local"

# Generar parámetros Diffie-Hellman
sudo openssl dhparam -out /etc/nginx/dhparam.pem 2048
```

---

## 6. Verificación de la Configuración

Para comprobar que no hay errores de sintaxis y activar el sitio:

```bash
# 1. Crear enlace simbólico
sudo ln -sf /etc/nginx/sites-available/factorio.conf /etc/nginx/sites-enabled/

# 2. Desactivar el sitio por defecto de Nginx si aún existe
sudo rm -f /etc/nginx/sites-enabled/default

# 3. Validar sintaxis
sudo nginx -t

# 4. Si la comprobación es exitosa, recargar Nginx sin cortar conexiones activas
sudo systemctl reload nginx
```

### Comprobación de Cabeceras con `curl`
```bash
curl -I https://localhost/ -k
```
Compruebe que la respuesta contiene:
- `server_tokens off` (solo muestra `Server: nginx` sin números de versión).
- Cabeceras `Strict-Transport-Security`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`.
- Cabecera `Content-Security-Policy`.
