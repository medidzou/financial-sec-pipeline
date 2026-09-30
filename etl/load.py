"""
Script de chargement : insère les données extraites et transformées
dans PostgreSQL (tables assets, asset_prices, indicators).
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_or_create_asset_id(cur, symbol: str) -> int:
    cur.execute("SELECT id FROM assets WHERE symbol = %s", (symbol,))
    result = cur.fetchone()
    if result:
        return result[0]

    cur.execute(
        "INSERT INTO assets (symbol, name, asset_type) VALUES (%s, %s, %s) RETURNING id",
        (symbol, symbol, "unknown"),
    )
    return cur.fetchone()[0]


def load_prices(conn, df):
    with conn.cursor() as cur:
        for _, row in df.iterrows():
            asset_id = get_or_create_asset_id(cur, row["symbol"])

            cur.execute(
                """
                INSERT INTO asset_prices
                    (asset_id, price_date, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (asset_id, price_date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
                """,
                (
                    asset_id,
                    row["price_date"],
                    row["open_price"],
                    row["high_price"],
                    row["low_price"],
                    row["close_price"],
                    int(row["volume"]),
                ),
            )
    conn.commit()
    print(f"{len(df)} lignes de prix insérées/mises à jour.")


def load_indicators(conn, df):
    df = df.dropna(subset=["daily_return", "volatility", "moving_avg"])

    with conn.cursor() as cur:
        for _, row in df.iterrows():
            asset_id = get_or_create_asset_id(cur, row["symbol"])

            cur.execute(
                """
                INSERT INTO indicators
                    (asset_id, price_date, daily_return, volatility, moving_avg)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (asset_id, price_date) DO UPDATE SET
                    daily_return = EXCLUDED.daily_return,
                    volatility = EXCLUDED.volatility,
                    moving_avg = EXCLUDED.moving_avg
                """,
                (
                    asset_id,
                    row["price_date"],
                    round(float(row["daily_return"]), 4),
                    round(float(row["volatility"]), 4),
                    round(float(row["moving_avg"]), 4),
                ),
            )
    conn.commit()
    print(f"{len(df)} lignes d'indicateurs insérées/mises à jour.")


if __name__ == "__main__":
    from extract import fetch_market_data, SYMBOLS
    from transform import clean_data, compute_indicators, validate_data

    raw_data = fetch_market_data(SYMBOLS, period="1mo")
    cleaned = clean_data(raw_data)
    clean_df, rejected_df = validate_data(cleaned)
    if not rejected_df.empty:
           print(
               f"[!] ATTENTION : {len(rejected_df)} ligne(s) rejetée(s) par les contrôles qualité."
           )
    enriched = compute_indicators(cleaned)

    conn = get_connection()
    try:
        load_prices(conn, enriched)
        load_indicators(conn, enriched)
    finally:
        conn.close()

    print("Pipeline ETL terminé avec succès.")
