from datetime import datetime, timezone

import bcrypt
from sqlalchemy import text


ROLE_ANALYST = "analyst"
ROLE_AUDITOR = "auditor"
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    encoded_password = password.encode("utf-8")
    if len(encoded_password) < 12 or len(encoded_password) > 72:
        raise ValueError("Le mot de passe doit contenir entre 12 et 72 octets UTF-8.")
    return bcrypt.hashpw(encoded_password, bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeEncodeError):
        return False


def authenticate(engine, username: str, password: str):
    normalized_username = normalize_username(username)
    if not normalized_username or not password:
        return None

    with engine.begin() as connection:
        attempt = connection.execute(
            text(
                "SELECT locked_until FROM login_attempts "
                "WHERE username = :username FOR UPDATE"
            ),
            {"username": normalized_username},
        ).first()
        now = datetime.now(timezone.utc)
        if attempt and attempt.locked_until and attempt.locked_until > now:
            return None

        user = connection.execute(
            text(
                "SELECT id, username, password_hash, role FROM users "
                "WHERE username = :username"
            ),
            {"username": normalized_username},
        ).mappings().first()

        if user and verify_password(password, user["password_hash"]):
            connection.execute(
                text("DELETE FROM login_attempts WHERE username = :username"),
                {"username": normalized_username},
            )
            connection.execute(
                text(
                    "INSERT INTO audit_logs (user_action, details, status) "
                    "VALUES (:action, :details, :status)"
                ),
                {
                    "action": "LOGIN_SUCCESS",
                    "details": "Authentification réussie.",
                    "status": "SUCCESS",
                },
            )
            return {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
            }

        connection.execute(
            text(
                "INSERT INTO login_attempts (username, failed_attempts, last_attempt_at) "
                "VALUES (:username, 1, CURRENT_TIMESTAMP) "
                "ON CONFLICT (username) DO UPDATE SET "
                "failed_attempts = CASE "
                "  WHEN login_attempts.last_attempt_at < CURRENT_TIMESTAMP "
                "    - make_interval(mins => :lockout_minutes) "
                "  THEN 1 ELSE login_attempts.failed_attempts + 1 END, "
                "locked_until = CASE "
                "  WHEN (CASE "
                "    WHEN login_attempts.last_attempt_at < CURRENT_TIMESTAMP "
                "      - make_interval(mins => :lockout_minutes) "
                "    THEN 1 ELSE login_attempts.failed_attempts + 1 END) "
                ">= :max_failed_attempts "
                "  THEN CURRENT_TIMESTAMP + make_interval(mins => :lockout_minutes) "
                "  ELSE NULL END, "
                "last_attempt_at = CURRENT_TIMESTAMP"
            ),
            {
                "username": normalized_username,
                "lockout_minutes": LOCKOUT_MINUTES,
                "max_failed_attempts": MAX_FAILED_ATTEMPTS,
            },
        )
        connection.execute(
            text(
                "INSERT INTO audit_logs (user_action, details, status) "
                "VALUES (:action, :details, :status)"
            ),
            {
                "action": "LOGIN_FAILURE",
                "details": "Échec d'authentification.",
                "status": "WARNING",
            },
        )
    return None