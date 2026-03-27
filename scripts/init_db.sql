CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS option_flows (
    id           BIGSERIAL,
    timestamp    TIMESTAMPTZ NOT NULL,
    symbol       VARCHAR(10) NOT NULL,
    strike       DECIMAL(10,2),
    expiry       DATE,
    put_call     CHAR(1),
    side         VARCHAR(10),
    premium      BIGINT,
    volume       INTEGER,
    oi           INTEGER,
    bid_price    DECIMAL(10,4),
    ask_price    DECIMAL(10,4),
    is_sweep     BOOLEAN DEFAULT false,
    is_dark_pool BOOLEAN DEFAULT false,
    score        SMALLINT,
    direction    VARCHAR(10),
    ai_note      TEXT,
    stock_price  DECIMAL(10,2),
    raw_identifier VARCHAR(64),
    PRIMARY KEY (id, timestamp)
);

SELECT create_hypertable('option_flows', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_flows_symbol_ts ON option_flows (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_flows_score_ts  ON option_flows (score DESC, timestamp DESC);

CREATE TABLE IF NOT EXISTS alert_rules (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER,
    symbol      VARCHAR(10),
    min_score   SMALLINT DEFAULT 70,
    direction   VARCHAR(10),
    min_premium BIGINT DEFAULT 10000000,
    push_wechat BOOLEAN DEFAULT true,
    active      BOOLEAN DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(64) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    wechat_openid VARCHAR(64),
    is_active     BOOLEAN DEFAULT true,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
