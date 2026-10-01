"""Script de transformation : nettoie les données brutes issues de extract.py

et calcule les indicateurs financiers (rendement, volatilité, moyenne mobile)
par actif (symbol).
"""

from datetime import datetime, timezone
import pandas as pd
from extract import SYMBOLS


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie le DataFrame : supprime doublons, trie par actif puis par date."""
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["symbol", "price_date"])
    df = df.sort_values(["symbol", "price_date"]).reset_index(drop=True)

    price_cols = ["open_price", "high_price", "low_price", "close_price"]

    # Interpolation par actif séparément, pour ne pas mélanger les séries
    df[price_cols] = df.groupby("symbol")[price_cols].transform(
        lambda x: x.interpolate(method="linear")
    )
    df = df.dropna(subset=price_cols)

    return df


def validate_data(
    df: pd.DataFrame, allowed_symbols: list[str] = SYMBOLS
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Contrôles Data Quality stricts :

    - Prix strictement positifs
    - Cohérence OHLC
    - Volume positif ou nul
    - Date <= aujourd'hui (UTC)
    - Symbole faisant partie du référentiel autorisé
    """
    if df.empty:
        return df, pd.DataFrame()

    df = df.copy()
    dates = pd.to_datetime(df["price_date"]).dt.date
    today = datetime.now(timezone.utc).date()

    mask = (
        # 1. Prix strictement positifs
        (df["close_price"] > 0)
        & (df["open_price"] > 0)
        & (df["high_price"] > 0)
        & (df["low_price"] > 0)
        # 2. Cohérence du chandelier (High au sommet, Low à la base)
        & (df["high_price"] >= df["low_price"])
        & (df["high_price"] >= df["open_price"])
        & (df["high_price"] >= df["close_price"])
        & (df["low_price"] <= df["open_price"])
        & (df["low_price"] <= df["close_price"])
        # 3. Volume positif ou nul
        & (df["volume"] >= 0)
        # 4. Temporalité et périmètre
        & (dates <= today)
        & (df["symbol"].isin(allowed_symbols))
    )

    clean_df = df[mask].reset_index(drop=True)
    rejected_df = df[~mask].reset_index(drop=True)
    return clean_df, rejected_df


def compute_indicators(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Ajoute les colonnes d'indicateurs financiers calculées par actif (symbol)."""
    if df.empty:
        return df

    df = df.copy()

    df["daily_return"] = df.groupby("symbol")["close_price"].pct_change() * 100

    df["volatility"] = (
        df.groupby("symbol")["daily_return"]
        .rolling(window=window)
        .std()
        .reset_index(level=0, drop=True)
    )

    df["moving_avg"] = (
        df.groupby("symbol")["close_price"]
        .rolling(window=window)
        .mean()
        .reset_index(level=0, drop=True)
    )

    return df


if __name__ == "__main__":
    from extract import fetch_market_data

    raw_data = fetch_market_data(SYMBOLS, period="1mo")
    cleaned = clean_data(raw_data)
    clean_df, rejected_df = validate_data(cleaned)
    enriched = compute_indicators(clean_df)

    if not rejected_df.empty:
        print(f"[!] Lignes rejetées : {len(rejected_df)}")

    print(
        enriched[
            [
                "symbol",
                "price_date",
                "close_price",
                "daily_return",
                "volatility",
                "moving_avg",
            ]
        ]
        .groupby("symbol")
        .tail(5)
    )