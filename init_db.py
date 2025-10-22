import psycopg2
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Carrega variáveis de ambiente de um arquivo .env (para teste local)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("Variável de ambiente DATABASE_URL não encontrada.")

conn = None
c = None

try:
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()

    # MUDANÇA: Trocado "INTEGER PRIMARY KEY" por "SERIAL PRIMARY KEY" (padrão do Postgres)
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        email TEXT,
        registered INTEGER DEFAULT 0
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id SERIAL PRIMARY KEY,
        description TEXT,
        amount REAL,
        date TEXT,
        urgency INTEGER,
        owner TEXT,
        paid INTEGER DEFAULT 0
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS incomes (
        id SERIAL PRIMARY KEY,
        description TEXT,
        amount REAL,
        date TEXT,
        owner TEXT
    )
    ''')

    conn.commit()
    print("Tabelas 'users', 'expenses', e 'incomes' verificadas/criadas.")

    # Pré-cadastrar os 5 possíveis usuários (sem senha ainda)
    allowed = ['alpe', 'bastos', 'doug', 'prlt', 'alberto']
    
    for u in allowed:
        # MUDANÇA: "INSERT OR IGNORE" não existe no Postgres,
        # então verificamos antes se o usuário já existe.
        # MUDANÇA: Trocado "?" por "%s" (padrão do psycopg2)
        c.execute("SELECT 1 FROM users WHERE username = %s", (u,))
        if c.fetchone() is None:
            c.execute('INSERT INTO users (username, registered) VALUES (%s, %s)', (u, 0))
            print(f"Usuário '{u}' pré-cadastrado.")
        else:
            print(f"Usuário '{u}' já existe.")

    conn.commit()
    print('DB inicializado com usuários permitidos:', allowed)

except Exception as e:
    print(f"Ocorreu um erro: {e}")
    if conn:
        conn.rollback() # Desfaz a transação em caso de erro
finally:
    if c:
        c.close()
    if conn:
        conn.close()
    print("Conexão com o banco fechada.")