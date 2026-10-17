import os
import sys
import psycopg2

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from security.auth import hash_password, normalize_username, ROLE_ANALYST, ROLE_AUDITOR
from etl.extract import fetch_market_data, SYMBOLS
from etl.transform import validate_data, compute_indicators
from etl.load import load_prices, load_indicators, log_audit

SUPABASE_URL = os.getenv("DATABASE_URL")
if not SUPABASE_URL:
    raise RuntimeError("Variable d'environnement DATABASE_URL manquante.")

def main():
    print("1. Connexion a Supabase...")
    conn = psycopg2.connect(SUPABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("2. Execution des scripts SQL d'initialisation...")
    for sql_file in ["sql/init/01_init.sql", "sql/init/02_security.sql"]:
        full_path = os.path.join(PROJECT_ROOT, sql_file)
        with open(full_path, "r", encoding="utf-8") as f:
            sql_content = f.read()
        print(f"   Execution de {sql_file}...")
        cur.execute(sql_content)
    print("   -> Tables creees avec succes !")

    print("3. Creation des comptes utilisateurs de demonstration...")
    demo_users = [
        ("mehdi", "Insa2026!Analyst", ROLE_ANALYST),
        ("auditeur", "Insa2026!Auditor", ROLE_AUDITOR),
    ]

    for username, raw_password, role in demo_users:
        norm_user = normalize_username(username)
        pwd_hash = hash_password(raw_password)
        cur.execute(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (username) DO UPDATE
            SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role;
            """,
            (norm_user, pwd_hash, role),
        )
        print(f"   Compte {norm_user} ({role}) configure !")

    print("4. Ingestion initiale des donnees financieres dans Supabase...")
    os.environ["DATABASE_URL"] = SUPABASE_URL
    raw_df = fetch_market_data(SYMBOLS, period="1mo")
    valid_df, _ = validate_data(raw_df)
    indicators_df = compute_indicators(valid_df)

    conn.autocommit = False
    load_prices(conn, valid_df)
    load_indicators(conn, indicators_df)
    log_audit(
        conn,
        action="CLOUD_INIT_ETL",
        status="SUCCESS",
        details=f"Initialisation reussie : {len(valid_df)} cours et {len(indicators_df)} indicateurs charges.",
    )
    conn.commit()
    conn.close()
    print("   -> Pipeline ETL execute et charge dans Supabase avec succes !")
    print("\nINITIALISATION SUPABASE 100% COMPLETE !")

if __name__ == "__main__":
    main()
