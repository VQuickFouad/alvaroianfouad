"""
Dependencias compartidas para la inyección en los endpoints de FastAPI.
Proporciona acceso uniforme a la base de datos, configuración y validaciones de seguridad.
"""
from typing import Generator
from sqlalchemy.orm import Session
from .config import Settings, get_settings
from .database import get_db

__all__ = ["get_db", "get_settings", "Settings", "Session"]
