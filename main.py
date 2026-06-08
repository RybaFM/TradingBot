import os
from dotenv import load_dotenv
from models import NewsAnalyzer, PortfolioOperator, Crawler
import sqlite3
import time

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

#start - 64,933.74 $
'''connection = sqlite3.connect('database.db')
cursor = connection.cursor()
cursor.execute("DELETE FROM operations_history")
cursor.execute("DELETE FROM stocks")
starting_portfolio = [
    ('META', 25),
    ('AAPL', 15),
    ('GOOGL', 20),
    ('MSFT', 12),
    ('TSLA', 8)
]
cursor.executemany("INSERT INTO stocks VALUES (?, ?)", starting_portfolio)
cursor.execute("DELETE FROM bot_variables")
cursor.execute('''
    #INSERT INTO bot_variables (id, dollars, cents, last_link) 
    #VALUES (1, 30000, 0, '')
''')
connection.commit()
connection.close()'''

def load_from_db():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    current_stocks = {}

    cursor.execute("SELECT * FROM stocks")
    rows = cursor.fetchall()
    for row in rows:
        current_stocks[row[0]] = row[1]

    cursor.execute("SELECT * FROM bot_variables")
    row = cursor.fetchall()[0]
    dollars = float(row[1])
    cents = float(row[2])
    latest_visited_url = row[3]
    budget = dollars + cents/100
    connection.close()
    print(current_stocks)
    return current_stocks, budget, latest_visited_url

for i in range(30):
    try:
        print(f'Iteration {i}')
        current_stocks, budget, latest_visited_url = load_from_db()
        mxTrdValue = 3000
        crawler = Crawler(
            latest_visited_url,
            NewsAnalyzer(API_KEY, mxTrdValue),
            PortfolioOperator(current_stocks, budget, mxTrdValue)
            )
        crawler.process_webpage("https://techcrunch.com/")
        crawler.evaluate_portfolio()
        time.sleep(60)
    except Exception as e:
        print(f'Error occured: {e}')


