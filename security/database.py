import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL


def create_database_engine():
    load_dotenv()
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
    except Exception:
        pass

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return create_engine(database_url, pool_pre_ping=True)

    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_PASSWORD ou DATABASE_URL est absent. Configurez-le dans l'environnement ou dans .env."
        )

    database_url_obj = URL.create(
        "postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER", "secfin_user"),
        password=password,
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "secfin_db"),
    )
    return create_engine(database_url_obj, pool_pre_ping=True)