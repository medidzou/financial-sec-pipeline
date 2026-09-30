import pandas as pd
from etl.transform import validate_data


def test_validate_data_rejette_prix_negatif_ou_nul():
    df = pd.DataFrame({"close_price": [10, 0, -5, 20]})
    resultat = validate_data(df)
    assert len(resultat) == 2
