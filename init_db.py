import sqlite3
from werkzeug.security import generate_password_hash

DB = 'studio_v2.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# users: id, username, password_hash, email, registered (0/1)
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password_hash TEXT,
    email TEXT,
    registered INTEGER DEFAULT 0
)
''')

# expenses: id, description, amount, date, urgency (0-low,1-med,2-high), owner, paid (0/1)
c.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY,
    description TEXT,
    amount REAL,
    date TEXT,
    urgency INTEGER,
    owner TEXT,
    paid INTEGER DEFAULT 0
)
''')

# incomes: id, description, amount, date, owner
c.execute('''
CREATE TABLE IF NOT EXISTS incomes (
    id INTEGER PRIMARY KEY,
    description TEXT,
    amount REAL,
    date TEXT,
    owner TEXT
)
''')

# Pré-cadastrar os 5 possíveis usuários (sem senha ainda)
allowed = ['alpe', 'bastos', 'doug', 'prlt', 'alberto']
for u in allowed:
    try:
        c.execute('INSERT INTO users (username, registered) VALUES (?,?)', (u, 0))
    except Exception:
        pass

conn.commit()
conn.close()
print('DB inicializado com usuários permitidos:', allowed)
