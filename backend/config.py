"""
Configuración centralizada del backend basada en variables de entorno y Pydantic Settings.
Carga automáticamente las variables definidas en el archivo .env o en el entorno del sistema.
"""
import os
from functools import lru_cache
from pathlib import Path
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Soporte de reserva defensivo si pydantic-settings aún no está en el entorno
    from pydantic import BaseModel
    class BaseSettings(BaseModel):  # type: ignore
        def __init__(self, **values):
            import os
            from pathlib import Path
            env_vars = {}
            env_file = Path(".env")
            if env_file.is_file():
                try:
                    with open(env_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                k, v = line.split("=", 1)
                                env_vars[k.strip()] = v.strip().strip("'\"")
                except Exception:
                    pass
            for field in self.model_fields.keys():
                if field.upper() in os.environ:
                    env_vars[field] = os.environ[field.upper()]
                elif field in os.environ:
                    env_vars[field] = os.environ[field]
            env_vars.update(values)
            super().__init__(**env_vars)

    class SettingsConfigDict(dict):  # type: ignore
        pass


class Settings(BaseSettings):
    """
    Parámetros de configuración de la plataforma Factorio Tech Solutions.
    """
    APP_NAME: str = "Factorio Tech Solutions"
    DEBUG: bool = False
    DEMO_MODE: bool = True  # Habilitado por defecto según requerimiento
    DATABASE_URL: str = "sqlite:///./data/factorio.db"

    # Integraciones de observabilidad externa
    NETDATA_URL: str = "http://localhost:19999"
    LOKI_URL: str = "http://localhost:3100"

    # Integración con Inteligencia Artificial
    AI_PROVIDER: str = "none"  # 'openai', 'ollama' o 'none'
    AI_API_KEY: str = ""
    AI_API_KEY_FILE: str = ""
    AI_MODEL: str = "gpt-4o-mini"
    AI_BASE_URL: str = "https://api.openai.com/v1"

    # Notificaciones y alertas
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_TOKEN_FILE: str = ""
    TELEGRAM_ALLOWED_USERS: str = ""

    # Copias de seguridad
    RESTIC_REPOSITORY: str = ""
    RESTIC_PASSWORD: str = ""
    RESTIC_PASSWORD_FILE: str = ""
    RESTIC_BACKUP_PATHS: str = ""
    RESTIC_TIMEOUT_SECONDS: int = 300

    # Logs y Seguridad
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "factorio-secret-key-change-in-production-env"
    SECRET_KEY_FILE: str = ""
    AUTH_SETUP_TOKEN: str = ""
    AUTH_SETUP_TOKEN_FILE: str = ""
    SESSION_COOKIE_SECURE: bool = True
    SESSION_TTL_HOURS: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la instancia única de configuración en caché.
    """
    settings = Settings()
    for value_name in (
        "AI_API_KEY",
        "AUTH_SETUP_TOKEN",
        "RESTIC_PASSWORD",
        "SECRET_KEY",
        "TELEGRAM_BOT_TOKEN",
    ):
        file_name = getattr(settings, f"{value_name}_FILE")
        if not file_name:
            continue
        try:
            secret_value = Path(file_name).read_text(encoding="utf-8").rstrip("\r\n")
        except OSError as exc:
            raise RuntimeError(f"No se pudo leer el archivo configurado para {value_name}.") from exc
        if not secret_value:
            raise RuntimeError(f"El archivo configurado para {value_name} está vacío.")
        setattr(settings, value_name, secret_value)
    return settings
