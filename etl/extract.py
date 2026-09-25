import yfinance as yf
import pandas as pd

SYMBOLS = ["AAPL", "MSFT", "BTC-USD"]

def fetch_market_data(symbols: list, period: str = "5d") -> pd.DataFrame:
    records = []
    
    for symbol in symbols:
        print(f"[*] Téléchargement des cours pour {symbol}...")
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval="1d")
            
            if df.empty:
                print(f"[!] Aucune donnée pour {symbol}")
                continue
                
            df = df.reset_index()
            for _, row in df.iterrows():
                dt = row["Date"]
                p_date = dt.date() if hasattr(dt, "date") else dt
                
                records.append({
                    "symbol": symbol,
                    "price_date": p_date,
                    "open_price": round(float(row["Open"]), 4),
                    "high_price": round(float(row["High"]), 4),
                    "low_price": round(float(row["Low"]), 4),
                    "close_price": round(float(row["Close"]), 4),
                    "volume": int(row["Volume"])
                })
        except Exception as e:
            print(f"[!] Erreur sur {symbol}: {e}")
            
    return pd.DataFrame(records)

if __name__ == "__main__":
    df_prices = fetch_market_data(SYMBOLS)
    print("\n--- Aperçu des données extraites ---")
    if not df_prices.empty:
        print(df_prices.head(10))
        print(f"\nTotal lignes récupérées : {len(df_prices)}")
    else:
        print("Aucune donnée récupérée.")
