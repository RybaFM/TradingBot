from google import genai
import json
import time
import requests
from bs4 import BeautifulSoup
import sqlite3
import yfinance as yf

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

        1. RISK MANAGEMENT RULE: You are NOT allowed to spend all your money at once. The total cost of any single transaction (shares_count * estimated_price_mentioned) MUST NOT exceed ${self.max_trade_value}. 
           Adjust your "shares_count" dynamically for EACH company so that (shares_count * price) stays below ${self.max_trade_value}.

        2. TRANSACTION VOLUME RULE: "shares_count" must be an integer greater than 0 for each tracked ticker. Never 0.
        3. PRICE MANDATE: "estimated_price_mentioned" MUST be a valid number representing a recent approximate stock price. NEVER output null.

        JSON Structure to output (can contain multiple ticker blocks if applicable):
        {{
          "TICKER_1": {{
            "company_name": "Official Name 1",
            "action": "Buy" or "Sell",
            "shares_count": <integer_greater_than_0>,
            "estimated_price_mentioned": <number>
          }},
          "TICKER_2": {{
            "company_name": "Official Name 2",
            "action": "Buy" or "Sell",
            "shares_count": <integer_greater_than_0>,
            "estimated_price_mentioned": <number>
          }}
        }}
        """
        #must change this part so it will return not shares_count but friction [0, 1]
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
    
    def __init__(self, current_stocks, budget):
        self.current_stocks = current_stocks
        self.budget = budget

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
        
        for name in data.keys():
            stock_count = data[name]['shares_count']
            stock_price = self.get_actual_prices(name)
            
            if data[name]['action'] == 'Sell':
                if name in self.current_stocks:
                    stocks_to_sold = min(stock_count, self.current_stocks[name])
                    price_total = stocks_to_sold * stock_price
                    self.current_stocks[name] -= stocks_to_sold
                    self.budget += price_total
            else:
                while stock_count > 0:
                    if self.budget >= stock_count * stock_price:
                        break
                    stock_count -= 1
                price_total = stock_count * stock_price
                if name not in self.current_stocks:
                    self.current_stocks[name] = 0
                self.current_stocks[name] += stock_count
                self.budget -= price_total
            print(self.current_stocks)
            print(self.budget)
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
                (time_post[1] == 'hour' or time_post[1] == 'hours') and int(time_post[0]) <= 6):
                if i == 0: self.latest_visited_url = link
                links_to_process.append(link)
            else: break
            
        for link in reversed(links_to_process):
            self.process_article(link)
            time.sleep(3)

        self.save_url_to_database()
