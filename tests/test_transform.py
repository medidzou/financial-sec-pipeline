import pandas as pd
from etl.transform import validate_data


def test_validate_data_filters_invalid_prices():
    # Données de test : 1 ligne valide, 3 lignes aberrantes
    data = {
        "symbol": ["AAPL", "AAPL", "AAPL", "AAPL"],
        "price_date": ["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04"],
        "open_price": [150.0, -10.0, 150.0, 150.0],       # Ligne 2 : prix négatif
        "high_price": [155.0, 155.0, 140.0, 155.0],       # Ligne 3 : high < low (140 < 145)
        "low_price": [148.0, 148.0, 145.0, 0.0],          # Ligne 4 : prix nul
        "close_price": [152.0, 152.0, 142.0, 152.0],
    }
    df = pd.DataFrame(data)

    result = validate_data(df)

    # Seule la première ligne doit survivre
    assert len(result) == 1
    assert result.iloc[0]["price_date"] == "2026-03-01"
