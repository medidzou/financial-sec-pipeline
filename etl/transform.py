"""
Script de transformation : nettoie les données brutes issues de extract.py
et calcule les indicateurs financiers (rendement, volatilité, moyenne mobile)
par actif (symbol).
"""

import pandas as pd


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie le DataFrame : supprime doublons, trie par actif puis par date.
    """
    df = df.drop_duplicates(subset=["symbol", "price_date"])
    df = df.sort_values(["symbol", "price_date"]).reset_index(drop=True)

    price_cols = ["open_price", "high_price", "low_price", "close_price"]

    # Interpolation par actif séparément, pour ne pas mélanger les séries
    df[price_cols] = df.groupby("symbol")[price_cols].transform(
        lambda x: x.interpolate(method="linear")
    )
    df = df.dropna(subset=price_cols)

    return df

def validate_data(df):
    mask = (df["close_price"] > 0) & (df["high_price"] > 0) & (df["low_price"] > 0) & (df["open_price"] > 0) & (df["high_price"] >= df["low_price"]))
    return df[mask].reset_index(drop=True)

def compute_indicators(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Ajoute les colonnes d'indicateurs financiers, calculées séparément
    pour chaque actif (symbol) :
    - daily_return : rendement journalier en %
    - volatility   : écart-type glissant du rendement (sur `window` jours)
    - moving_avg   : moyenne mobile du prix de clôture (sur `window` jours)
    """
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
    from extract import fetch_market_data, SYMBOLS

    cleaned = clean_data(raw_data)
    validated = validate_data(cleaned)
    enriched = compute_indicators(validated)

    print(enriched[
        ["symbol", "price_date", "close_price", "daily_return", "volatility", "moving_avg"]
    ].groupby("symbol").tail(5))
