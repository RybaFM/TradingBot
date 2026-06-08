CREATE TABLE IF NOT EXISTS bot_variables (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  dollars INT,
  cents INT,
  last_link TEXT
);

CREATE TABLE IF NOT EXISTS stocks (
    stock_name TEXT PRIMARY KEY,
    stock_count INT
);

CREATE TABLE IF NOT EXISTS operations_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  stock_name TEXT,
  operation TEXT,
  stock_count INT,
  stock_price REAL,
  remaining_budget REAL,
  timestamp TEXT
);

CREATE TABLE portfolio_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_value REAL,
    timestamp TEXT
);