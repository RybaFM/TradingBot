import os
from dotenv import load_dotenv
from models import NewsAnalyzer, PortfolioOperator, Crawler
import sqlite3
import time

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def load_from_db():
    connection = sqlite3.connect('database.db')
    cursor = connection.cursor()
    current_stocks = {}

    #cursor.execute('''
    #    UPDATE bot_variables SET dollars = ?, cents = ?, last_link = ? WHERE id = 1
    #''', (30000, 0, ''))

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

'''cursor.execute("SELECT * FROM operations_history")
row = cursor.fetchall()
for i in row:
    print(i)

cursor.execute("SELECT * FROM stocks")
rows = cursor.fetchall()
for row in rows:
    print(row)'''

for i in range(3):
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
        time.sleep(60)
    except Exception as e:
        print(f'Error occured: {e}')


