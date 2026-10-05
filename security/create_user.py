import argparse
from getpass import getpass

from sqlalchemy import text

from security.auth import ROLE_ANALYST, ROLE_AUDITOR, hash_password, normalize_username
from security.database import create_database_engine


def main():
    parser = argparse.ArgumentParser(description="Créer un utilisateur du dashboard.")
    parser.add_argument("username")
    parser.add_argument("--role", choices=[ROLE_ANALYST, ROLE_AUDITOR], required=True)
    args = parser.parse_args()

    username = normalize_username(args.username)
    if not username:
        parser.error("L'identifiant ne peut pas être vide.")
    password = getpass("Mot de passe (12 à 72 octets UTF-8) : ")
    confirmation = getpass("Confirmez le mot de passe : ")
    if password != confirmation:
        parser.error("Les mots de passe ne correspondent pas.")

    password_hash = hash_password(password)
    engine = create_database_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (username, password_hash, role) "
                "VALUES (:username, :password_hash, :role)"
            ),
            {"username": username, "password_hash": password_hash, "role": args.role},
        )
    engine.dispose()
    print(f"Utilisateur {username} créé avec le rôle {args.role}.")


if __name__ == "__main__":
    main()