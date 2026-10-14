# Limitaciones Conocidas y Hoja de Ruta (Roadmap) ⚠️📌

Este documento describe con total transparencia el alcance actual de **Factorio Tech Solutions**, delimitando las capacidades operativas en cada modo de ejecución, los requisitos para producción real y las mejoras planificadas.

---

## 1. Alcance: Modo Demostración vs. Modo Producción Real

Para permitir la docencia y evaluación en entornos sin acceso a privilegios de `root` o sin infraestructura auxiliar, la plataforma cuenta con un conmutador `DEMO_MODE=true` en `.env`.

| Característica | Comportamiento en Modo Demo (`DEMO_MODE=true`) | Requerimientos en Modo Real (`DEMO_MODE=false`) |
| :--- | :--- | :--- |
| **Telemetría y Métricas** | Genera fluctuaciones sintéticas matemáticas verosímiles de CPU, RAM y E/S de disco. | Lee CPU, memoria, disco, red y procesos locales mediante `psutil`; la consulta de Netdata (`NETDATA_URL`) aún no está conectada como fuente de métricas. |
| **Agregación de Logs** | Emula eventos de log formateados y eventos de auditoría predefinidos. | Requiere `loki` activo en `LOKI_URL` (`:3100`) y `promtail` recopilando registros de `/var/log`. |
| **Copias de Seguridad** | Simula la generación de snapshots y la verificación de integridad de forma segura. | Requiere el binario `restic` en el `PATH` del sistema y un repositorio inicializado (`restic init`). |
| **Auditoría de Hardening** | Simula una inspección de directivas sobre una plantilla representativa de Ubuntu. | Requiere permisos de lectura sobre `/etc/ssh/sshd_config`, `/proc/sys/net/` y utilidades `ufw`/`fail2ban-client`. |
| **Bot de Telegram** | Simula la entrega de mensajes en consola de desarrollo si no hay token configurado. | Requiere un token válido emitido por `@BotFather` y conectividad HTTPS hacia los servidores de Telegram. |
| **Inteligencia Artificial** | Emula el motor con respuestas pregrabadas basadas en heurística de soporte Linux. | Requiere instancia local de `ollama` levantada o una clave de API válida de `openai`. |

---

## 2. Consideraciones y Limitaciones de Seguridad Actuales

1. **Aislamiento de la Base de Datos:**
   - La base de datos es SQLite. Es idónea para instalaciones en un único servidor y elimina la exposición de puertos de base de datos en la red. Sin embargo, no está concebida para clústeres distribuidos activo-activo ni concurrencia masiva de escrituras de miles de transacciones por segundo.
2. **Dependencia de Permisos de Sistema:**
   - La aplicación web corre deliberadamente bajo un usuario no privilegiado (`factorio`). Las consultas usan adaptadores de solo lectura y las acciones se limitan a una lista fija. Reiniciar Nginx requiere privilegios que no se conceden por defecto; el endpoint marca y audita el fallo en vez de escalar privilegios. No se deben conceder permisos sudo generales al proceso web.
3. **Validación de Modelos de Inteligencia Artificial:**
   - A pesar de que el motor de sanitización anonimiza de forma exhaustiva IPs, contraseñas y certificados, los modelos de lenguaje pueden generar "alucinaciones" (comandos sintácticamente incorrectos o no adaptados a versiones concretas). **Siempre** se advierte al administrador que revise cualquier comando sugerido antes de ejecutarlo.

---

## 3. Hoja de Ruta y Mejoras Futuras (Roadmap)

- [ ] **Gestión Multi-Servidor (Factorio Agent):**
  - Desarrollar un agente ligero en Go o Rust para instalar en múltiples servidores secundarios y gestionarlos desde un único panel centralizado de Factorio.
- [ ] **Soporte Nativo de Doble Factor de Autenticación (2FA / MFA):**
  - Integración de TOTP (Google Authenticator / FreeOTP) y llaves de seguridad físicas WebAuthn/FIDO2 para el acceso al panel administrativo.
- [ ] **Módulo WAF Avanzado (Web Application Firewall):**
  - Incorporación guiada de reglas OWASP ModSecurity Core Rule Set (CRS) y soporte nativo para CrowdSec con motor de reputación global.
- [ ] **Automatización de Certificados Wildcard DNS:**
  - Soporte para validación de certificados Let's Encrypt mediante desafíos DNS (DNS-01) con Cloudflare, OVH y AWS Route53.
- [ ] **Exportador de Informes de Cumplimiento Normativo:**
  - Generación de informes en PDF para auditorías de cumplimiento con el Esquema Nacional de Seguridad (ENS) de España y el estándar ISO 27001.
