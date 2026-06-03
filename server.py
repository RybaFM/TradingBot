from flask import Flask, render_template, g
import sqlite3
    
app = Flask(__name__)
    
def connect_db():
    return sqlite3.connect('database.db')
    
@app.before_request
def before_request():
    g.db = connect_db()
    
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()
    
@app.route('/')
def home():
    cursor = g.db.cursor()
    cursor.execute('''
        SELECT timestamp, remaining_budget 
        FROM operations_history 
        ORDER BY id ASC
    ''')
    rows = cursor.fetchall()
    chart_data = [[row[0], float(row[1])] for row in rows]

    cursor.execute('''
        SELECT COUNT(id) as count, stock_name
        FROM operations_history
        GROUP BY stock_name
        ORDER BY count DESC
    ''')
    rows2 = cursor.fetchall()
    most_popular_stocks = [[row[1], row[0]] for row in rows2]

    cursor.execute('''
        SELECT SUM(stock_count), operation
        FROM operations_history
        GROUP BY operation
    ''')
    rows3 = cursor.fetchall()
    buy_sell_fraction = [[row[1], row[0]] for row in rows3]
    
    return render_template('main.html',
                           chart_data=chart_data,
                           most_popular_stocks=most_popular_stocks,
                           buy_sell_fraction=buy_sell_fraction)

if __name__ == '__main__':
    app.run(debug=True)
