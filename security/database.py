import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


def create_database_engine():
    load_dotenv()
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_PASSWORD est absent. Configurez-le dans l'environnement ou dans .env."
        )

    database_url = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "secfin_user"),
        password=password,
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "secfin_db"),
    )
    return create_engine(database_url, pool_pre_ping=True)