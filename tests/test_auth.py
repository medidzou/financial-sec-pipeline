import pytest

from security.auth import hash_password, normalize_username, verify_password
from security.database import create_database_engine


def test_password_hash_is_salted_and_verifiable():
    password = "Correct-Horse-Battery-Staple-2026"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert not verify_password("wrong-password", first_hash)


def test_password_must_have_at_least_twelve_characters():
    with pytest.raises(ValueError):
        hash_password("too-short")


def test_username_is_normalized():
    assert normalize_username("  Mehdi  ") == "mehdi"


def test_database_url_preserves_reserved_password_characters(monkeypatch):
    password = "pa@ss/word:with?symbols"
    monkeypatch.setenv("POSTGRES_PASSWORD", password)
    monkeypatch.setenv("POSTGRES_USER", "secfin_user")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "secfin_db")

    engine = create_database_engine()

    assert engine.url.password == password
    engine.dispose()


def test_database_engine_requires_password(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "")

    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        create_database_engine()