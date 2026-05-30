from google import genai
import json
import time
import requests
from bs4 import BeautifulSoup
import sqlite3
import yfinance as yf
import math

class NewsAnalyzer:
    
    def __init__(self, apiKey, maxTrdValue):
        self.client = genai.Client(api_key=apiKey)
        self.max_trade_value = maxTrdValue

    def convert_to_dict(self, ai_response_string):
        clean_string = ai_response_string.strip()
        
        assert clean_string.startswith("{") and clean_string.endswith("}"), "Malformed string structure"
            
        try:
            result_dict = json.loads(clean_string)
            assert isinstance(result_dict, dict), "Parsed payload did not resolve to a Python dictionary"
            return result_dict
            
        except json.JSONDecodeError as err:
            raise AssertionError(f"String contents failed to parse into valid JSON syntax: {err}")

    def predict(self, article_text, current_stocks, budget):
        if not article_text:
            return

        # Using the exact ID from your successful list: gemini-3.1-flash-lite
        # Note: We remove the 'models/' prefix as the SDK adds it automatically
        model_id = "gemini-3.1-flash-lite"
        system_instruction = f"""
        You are an automated algorithmic trading assistant built for a university simulation project. 
        Your code will run continuously for hours, analyzing a continuous stream of articles.

        YOUR PROJECT PORTFOLIO STATUS:
        - Stocks you own right now: {current_stocks}
        - Available cash: ${budget}

        YOUR TRADING POLICY:
        You are a high-frequency, active demo trader. Do not be overly conservative. Evaluate the text for ANY market trends, product announcements, or executive news. An article may discuss one company, multiple companies, or none. 

        UNBREAKABLE TRADING RULES:
        0. STRATEGY (MULTI-COMPANY SUPPORT): 
           - Evaluate EVERY company mentioned. You are allowed to return multiple ticker keys in a single response if multiple companies have news.
           - If a company with a public stock ticker has even SLIGHTLY positive news, trigger a "Buy".
           - If the news is slightly negative, trigger a "Sell" (Short selling is allowed if we don't own it).
           - Only return {{}} if the article absolutely does not mention any known publicly traded companies.

        1. RISK MANAGEMENT RULE (CAPITAL ALLOCATION CONSTRAINTS):
           Instead of predicting share counts, you must provide a "confidence_weight" fraction strictly between 0.0 and 1.0. How you interpret this fraction depends entirely on the action:
           
           - FOR 'Buy' OPERATIONS: The "confidence_weight" represents the fraction of our maximum transaction budget (${self.max_trade_value}) to spend.
             *CRITICAL MULTI-ASSET RULE:* If you trigger multiple "Buy" actions in this single response, the SUM of all your "confidence_weight" values across all buy signals MUST NOT exceed 1.0 combined (to protect total liquidity).
           
           - FOR 'Sell' OPERATIONS: The "confidence_weight" represents the fraction of our CURRENT OWNED INVENTORY of that specific stock to sell (e.g., 0.5 means sell half of what we currently own). If we do not own the stock, scale it against the max transaction budget for a short sale.

        2. TRANSACTION VOLUME RULE: "confidence_weight" must be a raw floating-point number strictly between 0.0 and 1.0. Never 0.

        JSON Structure to output (can contain multiple ticker blocks if applicable):
        {{
          "TICKER_1": {{
            "company_name": "Official Name 1",
            "action": "Buy" or "Sell",
            "confidence_weight": <float_between_0.0_and_1.0>
          }},
          "TICKER_2": {{
            "company_name": "Official Name 2",
            "action": "Buy" or "Sell",
            "confidence_weight": <float_between_0.0_and_1.0>
          }}
        }}
        """
        try:
            response = self.client.models.generate_content(
                model=model_id,
                config={
                    "system_instruction": system_instruction,
                    "response_mime_type": "application/json"
                },
                contents=article_text
            )
            print(f"--- AI SENTIMENT ({model_id}) ---")
            print(response.text)
            data = self.convert_to_dict(response.text)
            return data
            
        except Exception as e:
            if "429" in str(e):
                print("Rate limit hit! Waiting 15 seconds...")
                time.sleep(15)
            else:
                print(f"AI API Error: {e}")


class PortfolioOperator:
    
    def __init__(self, current_stocks, budget, maxTrdValue):
        self.current_stocks = current_stocks
        self.budget = budget
        self.max_trade_value = maxTrdValue

    def get_current_stocks(self):
        return self.current_stocks

    def get_budget(self):
        return self.budget

    def get_actual_prices(self, stock):
        try:
            ticker = yf.Ticker(stock.upper())
            price = ticker.fast_info['lastPrice']
            print(price)
            return float(price)
        except Exception as e:
            print(f"Error occured: {e}")

    def save_to_db(self):
        total = int(round(self.budget * 100))
        dollars = total // 100
        cents = total % 100
        
        with sqlite3.connect('database.db') as connection:
            cursor = connection.cursor()
            cursor.execute('''
                UPDATE bot_variables
                SET dollars = ?, cents = ?
                WHERE id = 1
            ''', (dollars, cents))

            for stock in self.current_stocks:
                cursor.execute("""
                    INSERT INTO stocks (stock_name, stock_count)
                    VALUES (?, ?)
                    ON CONFLICT(stock_name) DO UPDATE SET stock_count = EXCLUDED.stock_count
                """, (stock, self.current_stocks[stock]))
            connection.commit()

    def process_data(self, data):
        if not data: return

        operations_history = []
        available_budget = min(self.budget, self.max_trade_value)
        for name in data.keys():
            stock_friction = data[name]['confidence_weight']
            stock_price = self.get_actual_prices(name)
            #maybe I should add two separate funcs sell_stocks, buy_stocks
            if data[name]['action'] == 'Sell':
                if name in self.current_stocks:
                    stocks_to_sell = math.floor(self.current_stocks[name]*stock_friction)
                    price_total = stocks_to_sell * stock_price
                    if stocks_to_sell != 0:
                        self.current_stocks[name] -= stocks_to_sell
                        self.budget += price_total
                        operations_history.append({'stock_name': name, 'operation': 'sell', 'count': stocks_to_sell, 'stock_price': stock_price, 'remaining_budget': self.budget})
            else:
                stocks_count = math.floor(self.max_trade_value*stock_friction/stock_price)
                price_total = stocks_count * stock_price
                if name not in self.current_stocks:
                    self.current_stocks[name] = 0
                if available_budget < price_total:
                    stocks_count = math.floor(available_budget/stock_price)
                    price_total = stocks_count * stock_price
                if available_budget >= price_total and stocks_count != 0:
                    self.current_stocks[name] += stocks_count
                    self.budget -= price_total
                    available_budget -= price_total
                    operations_history.append({'stock_name': name, 'operation': 'buy', 'count': stocks_count, 'stock_price': stock_price, 'remaining_budget': self.budget})
            print(self.current_stocks)
            print(self.budget)
            print(operations_history)
                    
        self.save_to_db()
        


class Crawler:

    def __init__(self, latest_visited_url, newsAnalyzer, portfolioOperator):
        self.latest_visited_url = latest_visited_url
        self.newsAnalyzer = newsAnalyzer
        self.portfolioOperator = portfolioOperator

    def get_last_visited_url(self):
        return self.latest_visited_url

    def process_article(self, link):
        text = requests.get(link).text
        parsed = BeautifulSoup(text, 'html.parser')
        paragraphs = parsed.select('main div > p.wp-block-paragraph')
        article = '\n'.join([paragraph.text.strip() for paragraph in paragraphs])
        data_to_process = self.newsAnalyzer.predict(article, self.portfolioOperator.get_current_stocks(), self.portfolioOperator.get_budget())
        self.portfolioOperator.process_data(data_to_process)
        print('\n\n\n')

    def save_url_to_database(self):
        with sqlite3.connect('database.db') as connection:
            cursor = connection.cursor()
            cursor.execute('''
                UPDATE bot_variables
                SET last_link = ?
                WHERE id = 1
            ''', (self.latest_visited_url,))
            connection.commit()
        
    def process_webpage(self, url0):
        text = requests.get(url0).text
        parsed = BeautifulSoup(text, 'html.parser')
        latest_news = parsed.select_one('.latest-news-section > div ul')
        elements = latest_news.select('li > div')

        links_to_process = []
        for i, element in enumerate(elements):
            link = element.select_one('h3.loop-card__title > a').get('href')
            if link == self.latest_visited_url: break
            time_post = element.select_one('time').text.strip().split(' ')
            if (time_post[1] == 'minute' or time_post[1] == 'minutes' or
                (time_post[1] == 'hour' or time_post[1] == 'hours') and int(time_post[0]) <= 15):
                if i == 0: self.latest_visited_url = link
                links_to_process.append(link)
            else: break
            
        for link in reversed(links_to_process):
            self.process_article(link)
            time.sleep(3)

        self.save_url_to_database()
