# Guía de Pruebas y Validación de Calidad (Testing) 🧪🎯

Esta guía describe el marco de pruebas de **Factorio Tech Solutions**, incluyendo la ejecución de pruebas unitarias, de integración, auditorías de seguridad automatizadas y procedimientos de validación en laboratorios.

---

## 1. Categorías de Pruebas

La suite de validación está dividida en cuatro niveles complementarios:

1. **Pruebas de Configuración y Sintaxis (L1):**
   - Validación del archivo `.env` y variables requeridas.
   - Verificación de sintaxis en scripts Bash mediante `bash -n`.
   - Comprobación de sintaxis de Nginx (`nginx -t`).
2. **Pruebas de Seguridad y Bastionado (L2):**
   - Comprobación de directivas en `/proc/sys` (parámetros de red del kernel).
   - Verificación de permisos estrictos en archivos sensibles (`chmod 600` en `.env`).
   - Comprobación de estado del firewall UFW y perfiles AppArmor.
3. **Pruebas de Integración y API Backend (L3):**
   - Endpoint de salud (`/api/health`).
   - Módulo de auditoría de seguridad y cálculo de métricas.
   - Verificación del comportamiento del modo demo (`DEMO_MODE=true`).
   - Sanitización del motor de IA ante inyecciones de datos sensibles.
4. **Pruebas de Copias de Seguridad (L4):**
   - Creación de instantánea sintética con Restic.
   - Comprobación de integridad con `restic check`.
   - Restauración y cálculo de hash criptográfico (checksum MD5/SHA256) de los datos recuperados frente a los originales.

---

## 2. Ejecución Automatizada de Pruebas

El proyecto incluye un ejecutable unificado para lanzar la batería de pruebas:

```bash
# Otorgar permisos si aún no los tiene
chmod +x scripts/run-tests.sh tests/test_integration.sh

# Ejecutar la suite completa
./scripts/run-tests.sh
```

Salida esperada:
```text
======================================================================
  FACTORIO TECH SOLUTIONS - SUITE DE PRUEBAS AUTOMATIZADAS
======================================================================
[*] Verificando sintaxis de scripts Shell...             [ OK ]
[*] Verificando permisos del entorno .env...            [ OK ]
[*] Verificando configuración y reglas UFW...           [ OK ]
[*] Ejecutando tests de integración y API...            [ OK ]
[*] Validando módulo de sanitización de IA...           [ OK ]
[*] Comprobando consistencia de copias de seguridad...  [ OK ]
----------------------------------------------------------------------
RESULTADO: Todas las pruebas superadas exitosamente (100% OK).
======================================================================
```

---

## 3. Pruebas de Integración con Bash (`tests/test_integration.sh`)

El archivo [tests/test_integration.sh](../tests/test_integration.sh) implementa aserciones directas mediante `curl` y llamadas al sistema sin depender de paquetes de testing pesados.

Para ejecutar únicamente el script de integración:
```bash
./tests/test_integration.sh
```

---

## 4. Procedimiento de Pruebas en Entorno de Laboratorio

Cuando se despliega el entorno en un aula formativa o máquina virtual de prueba:

### Paso 1: Prueba de Cortafuegos y Puertos Abiertos
Desde una máquina cliente en la misma red local:
```bash
# Escaneo de puertos con nmap
nmap -sT -p- <IP_DEL_SERVIDOR>
```
*Criterio de Aceptación:* Solo deben figurar abiertos el puerto SSH (22 o 2222) y los puertos web 80 y 443. Ningún puerto interno como 8000, 19999 o 3100 debe responder a IPs externas.

### Paso 2: Prueba de Fuerza Bruta y Baneo con Fail2ban
Desde la máquina cliente, intente fallar deliberadamente 5 intentos de autenticación SSH:
```bash
for i in {1..5}; do ssh -p 2222 usuarioinvalido@<IP_DEL_SERVIDOR>; done
```
*Criterio de Aceptación:* En el intento número 4 o 5, la conexión debe ser bloqueada inmediatamente (`Connection refused` o timeout). En el servidor, verificar con:
```bash
sudo fail2ban-client status sshd
```

### Paso 3: Prueba de Cabeceras de Seguridad Web
```bash
curl -I -k https://<IP_DEL_SERVIDOR>/
```
*Criterio de Aceptación:* Deben figurar en la respuesta HTTP:
- `Strict-Transport-Security`
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy`

### Paso 4: Prueba de Respaldo y Restauración Granular
```bash
# 1. Crear un archivo testigo en el directorio de datos
echo "dato-de-prueba-critico-$(date)" > /opt/factorio/app/data/testigo.txt

# 2. Ejecutar backup
./scripts/backup.sh

# 3. Borrar intencionadamente el archivo testigo
rm -f /opt/factorio/app/data/testigo.txt

# 4. Restaurar usando el script asistido
./scripts/restore.sh latest

# 5. Comprobar que el archivo testigo ha reaparecido intacto
cat /opt/factorio/app/data/testigo.txt
```

---

## 5. Cómo Agregar Nuevas Pruebas

Para agregar una nueva verificación al sistema:
1. Abra `tests/test_integration.sh`.
2. Cree una función descriptiva, por ejemplo `test_nueva_caracteristica()`:
   ```bash
   test_nueva_caracteristica() {
       log_info "Probando nueva característica..."
       # Lógica del test
       if [ condicion_correcta ]; then
           log_pass "Nueva característica operativa"
       else
           log_fail "Fallo detectado en nueva característica"
           return 1
       fi
   }
   ```
3. Llame a la función dentro de la rutina `main()` del script.
