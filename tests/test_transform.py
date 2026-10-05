from datetime import date, timedelta

import pandas as pd
import pytest

from etl.transform import compute_indicators, validate_data


def test_validate_data_filters_invalid_prices():
    # Données de test : 1 ligne valide, 3 lignes aberrantes
    data = {
        "symbol": ["AAPL", "AAPL", "AAPL", "AAPL"],
        "price_date": ["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04"],
        "open_price": [150.0, -10.0, 150.0, 150.0],       # Ligne 2 : prix négatif
        "high_price": [155.0, 155.0, 140.0, 155.0],       # Ligne 3 : high < low (140 < 145)
        "low_price": [148.0, 148.0, 145.0, 0.0],          # Ligne 4 : prix nul
        "close_price": [152.0, 152.0, 142.0, 152.0],
        "volume": [100, 100, 100, 100],
    }
    df = pd.DataFrame(data)

    clean_df, rejected_df = validate_data(df)

    # Seule la première ligne doit survivre
    assert len(clean_df) == 1
    assert len(rejected_df) == 3
    assert clean_df.iloc[0]["price_date"] == "2026-03-01"


def test_validate_data_rejects_future_dates():
    future_date = (date.today() + timedelta(days=1)).isoformat()
    data = {
        "symbol": ["AAPL"],
        "price_date": [future_date],
        "open_price": [150.0],
        "high_price": [155.0],
        "low_price": [148.0],
        "close_price": [152.0],
        "volume": [100],
    }

    clean_df, rejected_df = validate_data(pd.DataFrame(data))

    assert clean_df.empty
    assert len(rejected_df) == 1


def test_compute_indicators_uses_percentage_returns_and_five_day_average():
    df = pd.DataFrame(
        {
            "symbol": ["AAPL"] * 6,
            "price_date": pd.date_range("2026-01-01", periods=6),
            "close_price": [100.0, 110.0, 100.0, 120.0, 125.0, 150.0],
        }
    )

    result = compute_indicators(df)

    assert result.loc[1, "daily_return"] == pytest.approx(10.0)
    assert result.loc[2, "daily_return"] == pytest.approx(-100 / 11)
    assert result.loc[4, "moving_avg"] == pytest.approx(111.0)
    assert result.loc[5, "moving_avg"] == pytest.approx(121.0)
