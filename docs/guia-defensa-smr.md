# Guía para la Presentación y Defensa del Proyecto (Ciclo Formativo SMR) 🎓🛡️

Esta guía está diseñada para preparar y estructurar la defensa académica del proyecto de fin de ciclo formativo de **Sistemas Microinformáticos y Redes (SMR)** (y aplicable a **ASIR**). 

Contiene la estructura de la exposición, justificación técnica, relación con los módulos formativos oficiales, guion de demostración práctica (*demo script*) y un banco de preguntas y respuestas probables del tribunal evaluador.

---

## 1. Relación del Proyecto con los Módulos del Ciclo SMR

El proyecto **Factorio Tech Solutions** integra transversalmente las competencias de los principales módulos profesionales del currículo oficial:

| Módulo Profesional (SMR) | Competencia Aplicada en el Proyecto |
| :--- | :--- |
| **Seguridad Informática (SI)** | Bastionado del sistema operativo, reglas de cortafuegos UFW, prevención de intrusiones con Fail2ban, cifrado asimétrico en SSH, copias de seguridad criptográficas (Restic) y cabeceras HTTP seguras (HSTS, CSP). |
| **Sistemas Operativos en Red (SOR)** | Configuración avanzada de Linux (Ubuntu Server), gestión de usuarios y grupos restringidos, servicios en segundo plano con Systemd, temporizadores (*timers*), auditoría con `auditd` y control de procesos con AppArmor. |
| **Servicios en Red (SR)** | Despliegue y configuración del servidor web Nginx, configuración de proxy inverso, terminación TLS/SSL (HTTPS), resolución DNS local y direccionamiento TCP/IP. |
| **Redes Locales (RL)** | Segmentación de red, análisis de puertos abiertos con `ss` y `nmap`, configuración de subredes, tablas de enrutamiento y endurecimiento de la pila TCP/IP mediante `sysctl`. |
| **Aplicaciones Web (AW)** | Despliegue de aplicaciones web en producción, aislamiento de entornos con Python venv, integración de APIs REST y cuadros de mando en tiempo real. |

---

## 2. Estructura y Tiempos de la Exposición (15 Minutos)

Se recomienda organizar la presentación oral siguiendo este cronograma:

1. **Introducción y Problema (2 minutos):**
   - Contexto de las PYMEs: falta de personal especializado en ciberseguridad y servidores web desprotegidos.
   - Presentación de Factorio Tech Solutions como respuesta unificada y accesible.
2. **Arquitectura y Decisiones Técnicas (4 minutos):**
   - Mostrar el diagrama de arquitectura general (Nginx -> Core -> Seguridad -> Observabilidad).
   - Justificar la elección de herramientas ligeras y seguras (Restic, Netdata, Loki, SQLite en WAL).
3. **Demostración Práctica en Vivo (6 minutos):**
   - Seguir el guion de demo detallado en la sección 3.
4. **Seguridad y Bastionado (2 minutos):**
   - Explicar la política de defensa en profundidad y los resultados de la auditoría.
5. **Conclusiones y Trabajo Futuro (1 minuto):**
   - Logros alcanzados, cumplimiento de objetivos y posibles ampliaciones (ej. integración con WAF avanzado o agente multi-servidor).

---

## 3. Guion de Demostración Práctica (Demo Script Paso a Paso)

Siga este orden exacto durante la defensa para realizar una presentación fluida y sin tropiezos:

### Paso 1: Mostrar el Entorno y el Dashboard Principal (1 minuto)
- Abra el navegador web y acceda a `https://<ip-servidor>/` o `http://localhost:8000`.
- Comente: *"Como pueden observar, el panel ofrece de un vistazo la salud general del servidor, métricas en tiempo real y el estado del cortafuegos y copias de seguridad."*
- Destaque la carga de métricas (CPU, RAM, disco) provenientes del motor de telemetría.

### Paso 2: Auditoría de Seguridad y Bastionado en Acción (1.5 minutos)
- Vaya a la sección de **Seguridad y Hardening**.
- Muestre el resultado de la auditoría: estado de UFW, SSH en puerto seguro sin contraseñas, Fail2ban activo, parámetros sysctl.
- Ejecute en la terminal el script de auditoría rápida:
  ```bash
  ./scripts/check-security.sh
  ```
- Resalte: *"El sistema analiza de forma no intrusiva más de 10 puntos clave de la configuración del sistema operativo y asigna una puntuación de bastionado."*

### Paso 3: Demostración de Bloqueo con Fail2ban (1.5 minutos)
- Simule desde una segunda terminal o máquina varios accesos erróneos a SSH o a la API:
  ```bash
  ssh -p 2222 usuariofalso@127.0.0.1
  ```
- Muestre inmediatamente cómo Fail2ban detecta los intentos y añade la regla de bloqueo dinámico:
  ```bash
  sudo fail2ban-client status sshd
  ```
- Comente: *"El servidor reacciona automáticamente bloqueando al atacante en la capa de red mediante UFW."*

### Paso 4: Copia de Seguridad y Restauración con Restic (1 minuto)
- En la sección de backups o mediante consola, ejecute:
  ```bash
  ./scripts/backup.sh
  ```
- Muestre el snapshot generado con deduplicación y cifrado AES-256.
- Demuestre la integridad:
  ```bash
  ./scripts/verify-backup.sh
  ```
- Comente: *"Aplicamos la regla 3-2-1 con cifrado en origen, lo que garantiza que ni siquiera el proveedor de almacenamiento en la nube puede acceder al contenido."*

### Paso 5: Asistente IA con Sanitización y Bot de Telegram (1 minuto)
- Envíe una consulta con un dato confidencial simulado:
  > *"¿Por qué falla la IP 203.0.113.88 con password=SuperSecreta?"*
- Muestre en la consola o log cómo el sanitizador enmascara los datos antes de llamar al modelo.
- Muestre en Telegram la notificación recibida del estado del servidor.

---

## 4. Preguntas Frecuentes del Tribunal Evaluador y Respuestas Tipo

### P1: "¿Por qué habéis utilizado SQLite en lugar de MySQL o PostgreSQL?"
> **Respuesta:** *"Para un servidor de gestión único en una PYME, SQLite con modo WAL (Write-Ahead Logging) ofrece un rendimiento óptimo con latencia cero de red. Además, elimina un vector de ataque crítico: no hay un puerto de base de datos escuchando en la red externa ni necesidad de gestionar usuarios o contraseñas de conexión que puedan filtrarse. Se almacena en un archivo local protegido con permisos 600 y se respalda de forma atómica."*

### P2: "¿Qué ocurriría si el servidor se reinicia inesperadamente?"
> **Respuesta:** *"El servicio está configurado como una unidad de Systemd (`factorio.service`) con la directiva `Restart=always` y `RestartSec=5s`, habilitado para inicio automático en el arranque del sistema (`systemctl enable`). Asimismo, las copias de seguridad están programadas mediante `Systemd Timers`, por lo que si el equipo estaba apagado a la hora programada, la opción `Persistent=true` asegura que el respaldo se ejecute tan pronto el sistema vuelva a iniciar."*

### P3: "¿Por qué no habéis puesto la aplicación a correr directamente en el puerto 80/443 como root?"
> **Respuesta:** *"Por respeto estricto al Principio de Menor Privilegio (PoLP). Si la aplicación web sufriera una vulnerabilidad y estuviese corriendo como root, el atacante obtendría control total del servidor. Al ejecutarla bajo el usuario sin privilegios `factorio` y situar a Nginx como proxy inverso y terminador TLS, Nginx gestiona los puertos privilegiados (<1024), aplica filtros de seguridad (cabeceras, rate limit) y se comunica con la app localmente."*

### P4: "¿Cómo garantizáis la privacidad si se utiliza la Inteligencia Artificial?"
> **Respuesta:** *"Hemos implementado una capa intermedia de desinfección mediante expresiones regulares (`Data Redactor`). Antes de que cualquier mensaje o fragmento de log salga hacia el modelo (sea local o en la nube), el sistema detecta y enmascara direcciones IP públicas, privadas, tokens de acceso, certificados y contraseñas. Además, ofrecemos soporte nativo para modelos locales privados con Ollama, donde ningún dato sale jamás del servidor."*

### P5: "¿Qué diferencia hay entre una copia incremental normal y la que hace Restic?"
> **Respuesta:** *"Las copias incrementales tradicionales dependen de una cadena de backups diferenciales donde si falla una copia intermedia, se compromete la restauración. Restic utiliza deduplicación a nivel de bloques de tamaño variable y almacena cada snapshot como si fuera una copia completa independiente, pero ocupando únicamente el espacio de los bloques nuevos o modificados, todo ello protegido criptográficamente."*
