CREATE TABLE bot_variables (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  dollars INT,
  cents INT,
  last_link TEXT
);

CREATE TABLE stocks (
    stock_name TEXT PRIMARY KEY,
    stock_count INT
);