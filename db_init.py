import sqlite3
connection = sqlite3.connect('database.db')
cursor = connection.cursor()
with open('create_db.sql', 'r') as file:
    sql_script = file.read()
cursor.executescript(sql_script)
connection.commit()
connection.close()
