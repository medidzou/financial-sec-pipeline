CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(100),
    asset_type VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_prices (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES assets(id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    open_price NUMERIC(12, 4),
    high_price NUMERIC(12, 4),
    low_price NUMERIC(12, 4),
    close_price NUMERIC(12, 4),
    volume BIGINT,
    UNIQUE(asset_id, price_date)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_action VARCHAR(50) NOT NULL,
    details TEXT,
    status VARCHAR(20) NOT NULL
);

INSERT INTO assets (symbol, name, asset_type) VALUES
('AAPL', 'Apple Inc.', 'stock'),
('MSFT', 'Microsoft Corporation', 'stock'),
('BTC-USD', 'Bitcoin USD', 'crypto')
ON CONFLICT (symbol) DO NOTHING;



CREATE TABLE IF NOT EXISTS indicators (
    id BIGSERIAL PRIMARY KEY,
    asset_id INT REFERENCES assets(id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    daily_return NUMERIC(10, 4),
    volatility NUMERIC(10, 4),
    moving_avg NUMERIC(12, 4),
    UNIQUE(asset_id, price_date)
);
