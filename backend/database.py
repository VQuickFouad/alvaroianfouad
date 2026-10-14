"""
Gestión de conexión y sesiones para la base de datos SQLite con SQLAlchemy.
Garantiza la inicialización automática de esquemas y provee la dependencia de sesión.
"""
import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings
from .models.database_models import Base

settings = get_settings()

# Asegurar que el directorio contenedor de la base de datos exista
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_file_path = Path(db_url.replace("sqlite:///", ""))
    db_file_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Inicializa todas las tablas del modelo relacional en la base de datos.
    Crea automáticamente: alerts, actions, backup_records, automation_tasks, config_entries, audit_log.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Generador de dependencias de FastAPI para inyectar sesiones de base de datos.
    Garantiza el cierre seguro de la conexión al finalizar el ciclo de vida de la petición.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
