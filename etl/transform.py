"""
Script de transformation : nettoie les données brutes et calcule
les indicateurs financiers (rendement, volatilité, moyenne mobile).
"""

import pandas as pd


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie le DataFrame : supprime doublons, gère les valeurs manquantes,
    trie par date.
    """
    df = df.drop_duplicates(subset=["Date", "ticker"])
    df = df.sort_values("Date").reset_index(drop=True)

    price_cols = ["Open", "High", "Low", "Close"]
    df[price_cols] = df[price_cols].interpolate(method="linear")
    df = df.dropna(subset=price_cols)

    return df


def compute_indicators(df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
    """
    Ajoute les colonnes d'indicateurs financiers :
    - daily_return : rendement journalier en %
    - volatility : écart-type glissant du rendement (sur `window` jours)
    - moving_avg : moyenne mobile du prix de clôture (sur `window` jours)
    """
    df = df.copy()

    df["daily_return"] = df["Close"].pct_change() * 100
    df["volatility"] = df["daily_return"].rolling(window=window).std()
    df["moving_avg"] = df["Close"].rolling(window=window).mean()

    return df


if __name__ == "__main__":
    from extract import fetch_asset_data

    raw_data = fetch_asset_data("AAPL", period="1mo")
    cleaned = clean_data(raw_data)
    enriched = compute_indicators(cleaned)

    print(enriched[["Date", "Close", "daily_return", "volatility", "moving_avg"]].tail(10))
