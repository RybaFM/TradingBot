import os
from dotenv import load_dotenv
from models import NewsAnalyzer, PortfolioOperator, Crawler

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# PortfolioOperator | Later from db
current_stocks = {'TTWO': 5, 'SPOT': 5, 'AAPL': 10, 'GOOGL': 10, 'MSFT': 5, 'NVDA': 10, 'META': 5}
budget = 30000
# Crawler | Later from db
latest_visited_url = ''


crawler = Crawler(
    latest_visited_url,
    NewsAnalyzer(API_KEY, 3000),
    PortfolioOperator(current_stocks, budget)
    )
crawler.process_webpage("https://techcrunch.com/")
