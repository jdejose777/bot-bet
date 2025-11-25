"""setup_db
Inicializa la base de datos SQLite para el sistema de Value Betting.

Diseño del esquema (versión 2):

Tabla matches:
    - id INTEGER PRIMARY KEY AUTOINCREMENT
    - home_team TEXT NOT NULL
    - away_team TEXT NOT NULL
    - league TEXT NOT NULL
    - match_datetime TEXT NOT NULL (UTC, ISO 8601: YYYY-MM-DDTHH:MM:SSZ)
    - status TEXT NOT NULL DEFAULT 'scheduled' (scheduled|in_progress|finished|postponed|cancelled)
    - created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    - updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    UNIQUE(home_team, away_team, league, match_datetime)

Tabla odds (histórico de snapshots de cuotas):
    - id INTEGER PRIMARY KEY AUTOINCREMENT
    - match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE
    - bookmaker TEXT NOT NULL
    - odds_home REAL NOT NULL
    - odds_draw REAL NOT NULL
    - odds_away REAL NOT NULL
    - extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    Índices para consultas por match y bookmaker.

Buenas prácticas aplicadas:
    - Activación de foreign_keys.
    - Creación idempotente del esquema.
    - Manejo básico de errores y mensajes claros.
    - Type hints y docstrings.
"""
from __future__ import annotations

import os
import sqlite3
from sqlite3 import Error
from typing import Optional

# Rutas
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
DB_PATH = os.path.join(DATA_DIR, 'value_betting.db')


def create_connection(db_path: str = DB_PATH) -> Optional[sqlite3.Connection]:
    """Crea y retorna una conexión SQLite, activando foreign keys.

    Args:
        db_path: Ruta absoluta al archivo .db

    Returns:
        Conexión SQLite lista para usar o None si falla.
    """
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        print(f"[DB] Conexión establecida: {db_path}")
        return conn
    except Error as exc:  # noqa: BLE001 (simplificación controlada)
        print(f"[DB][ERROR] Falló la conexión: {exc}")
        return None


MATCHES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    league TEXT NOT NULL,
    match_datetime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(home_team, away_team, league, match_datetime)
);
"""

ODDS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS odds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    bookmaker TEXT NOT NULL,
    odds_home REAL NOT NULL,
    odds_draw REAL NOT NULL,
    odds_away REAL NOT NULL,
    extracted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (match_id) REFERENCES matches (id) ON DELETE CASCADE
);
"""

INDEXES_SQL = [
    # Optimiza búsquedas por partido + casa
    "CREATE INDEX IF NOT EXISTS idx_odds_match_bookmaker ON odds(match_id, bookmaker);",
    # Optimiza series temporales de cuotas por partido
    "CREATE INDEX IF NOT EXISTS idx_odds_match_extracted ON odds(match_id, extracted_at);",
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Crea tablas e índices si no existen.

    Args:
        conn: Conexión SQLite abierta.
    """
    try:
        cur = conn.cursor()
        print("[DB] Creando tabla matches...")
        cur.execute(MATCHES_TABLE_SQL)
        print("[DB] Creando tabla odds...")
        cur.execute(ODDS_TABLE_SQL)
        print("[DB] Creando índices...")
        for stmt in INDEXES_SQL:
            cur.execute(stmt)
        conn.commit()
        print("[DB] Esquema OK.")
    except Error as exc:  # noqa: BLE001
        print(f"[DB][ERROR] Falló creación de esquema: {exc}")


def initialize_database(db_path: str = DB_PATH) -> bool:
    """Inicializa la base de datos completa.

    Args:
        db_path: Ruta donde se almacena el archivo .db.

    Returns:
        True si se creó/verificó el esquema correctamente, False si hubo errores.
    """
    conn = create_connection(db_path)
    if conn is None:
        return False
    create_schema(conn)
    conn.close()
    return True


def main() -> None:
    """Punto de entrada CLI para inicializar la DB."""
    print("--- Inicializando base de datos Value Betting ---")
    ok = initialize_database()
    if ok:
        print("--- Base de datos lista ---")
    else:
        print("--- Error al inicializar la base de datos ---")


if __name__ == "__main__":
    main()
