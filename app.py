import os
import psycopg2 # MUDANÇA: Sai sqlite3, entra psycopg2
from psycopg2.extras import RealDictCursor # Para os resultados parecerem dicionários
import secrets
from datetime import datetime
from functools import wraps # Para o @login_required

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from dotenv import load_dotenv # Para facilitar testes locais

# Carrega variáveis de ambiente de um arquivo .env (se existir)
load_dotenv()

app = Flask(__name__)

# MUDANÇA: Pega as chaves do ambiente. 
# Você PRECISA configurar DATABASE_URL e SECRET_KEY no Render.
DATABASE_URL = os.environ.get('DATABASE_URL')
SECRET_KEY = os.environ.get('SECRET_KEY', 'default-fallback-key-mude-isso')

if not DATABASE_URL:
    raise ValueError("A variável de ambiente DATABASE_URL não foi definida.")

app.config['SECRET_KEY'] = SECRET_KEY

# Configuração do Flask-Mail (lendo do ambiente)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config.get('MAIL_USERNAME'))

mail = Mail(app)

def get_db_conn():
    """ MUDANÇA: Abre uma conexão com o banco PostgreSQL. """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

# MUDANÇA: Wrapper de login para limpar o código
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Por favor, faça login para acessar esta página.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if session.get('user'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        conn = None
        cur = None
        try:
            conn = get_db_conn()
            if conn is None:
                flash('Erro de conexão com o banco.', 'danger')
                return render_template('login.html')
            
            # MUDANÇA: cur.execute e %s
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()

            if user and user['registered'] == 1 and check_password_hash(user['password_hash'], password):
                session['user'] = username
                flash('Logado com sucesso!', 'success')
                return redirect(url_for('dashboard'))
            
            flash('Usuário/senha incorretos ou usuário não registrado.', 'danger')
        
        except Exception as e:
            flash(f'Erro no login: {e}', 'danger')
        
        finally:
            if cur: cur.close()
            if conn: conn.close()
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Desconectado.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        email = request.form['email'].strip()
        
        conn = None
        cur = None
        try:
            conn = get_db_conn()
            if conn is None:
                flash('Erro de conexão com o banco.', 'danger')
                return render_template('register.html')

            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()

            if not user:
                flash('Nome de usuário não permitido.', 'danger')
                return redirect(url_for('register'))
            
            if user['registered'] == 1:
                flash('Usuário já registrado. Faça login ou use esqueci a senha.', 'warning')
                return redirect(url_for('login'))

            pw_hash = generate_password_hash(password)
            cur.execute('UPDATE users SET password_hash = %s, email = %s, registered = 1 WHERE username = %s', 
                        (pw_hash, email, username))
            conn.commit()
            flash('Cadastro realizado! Agora faça login.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Erro no registro: {e}', 'danger')
            if conn: conn.rollback()
        
        finally:
            if cur: cur.close()
            if conn: conn.close()

    return render_template('register.html')

@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        username = request.form['username'].strip()
        
        conn = None
        cur = None
        try:
            conn = get_db_conn()
            if conn is None:
                flash('Erro de conexão com o banco.', 'danger')
                return render_template('forgot.html')

            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cur.fetchone()

            if not user or not user['email']:
                flash('Usuário não encontrado ou sem e-mail cadastrado.', 'danger')
                return redirect(url_for('forgot'))

            temp_pw = secrets.token_urlsafe(8)
            pw_hash = generate_password_hash(temp_pw)
            cur.execute('UPDATE users SET password_hash = %s WHERE username = %s', (pw_hash, username))
            conn.commit()

            try:
                msg = Message('Recuperação de senha - Studio', recipients=[user['email']])
                msg.body = f"Olá {username},\n\nRecebemos um pedido de recuperação de senha. Sua senha temporária é: {temp_pw}\nPor favor, entre e altere sua senha depois.\n\n— Equipe do Studio"
                mail.send(msg)
                flash('E-mail enviado com senha temporária.', 'info')
            except Exception as e:
                print('Erro enviando e-mail:', e)
                flash('Falha ao enviar e-mail. Verifique a configuração do servidor de e-mail.', 'danger')
            
            return redirect(url_for('login'))

        except Exception as e:
            flash(f'Erro: {e}', 'danger')
            if conn: conn.rollback()
        
        finally:
            if cur: cur.close()
            if conn: conn.close()
            
    return render_template('forgot.html')

@app.route('/dashboard')
@login_required # MUDANÇA: Adicionado wrapper
def dashboard():
    user = session['user']
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # MUDANÇA: IFNULL -> COALESCE
        cur.execute('SELECT COALESCE(SUM(amount),0) as total FROM incomes')
        total_income = cur.fetchone()['total']
        
        cur.execute('SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE paid = 1')
        total_spent = cur.fetchone()['total']
        
        cur.execute('SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE paid = 0')
        total_pending = cur.fetchone()['total']
        
        total_available = total_income - total_spent
        
        cur.execute('SELECT * FROM expenses ORDER BY date DESC LIMIT 10')
        recent = cur.fetchall()
        
        return render_template('dashboard.html', 
                               user=user, 
                               total_income=total_income, 
                               total_spent=total_spent, 
                               total_pending=total_pending, 
                               total_available=total_available, 
                               recent=recent)
    except Exception as e:
        flash(f'Erro ao carregar dashboard: {e}', 'danger')
        return render_template('dashboard.html', user=user)
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route('/add', methods=['GET','POST'], endpoint='add')
@login_required # MUDANÇA: Adicionado wrapper
def add_expense():
    if request.method == 'POST':
        desc = request.form['description']
        amount = float(request.form['amount'])
        date = request.form['date'] or datetime.now().strftime('%Y-%m-%d')
        urgency = int(request.form.get('urgency','0'))
        owner = session['user']
        
        conn = None
        cur = None
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            # MUDANÇA: %s
            cur.execute('INSERT INTO expenses (description, amount, date, urgency, owner) VALUES (%s,%s,%s,%s,%s)', 
                        (desc, amount, date, urgency, owner))
            conn.commit()
            flash('Despesa adicionada.', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            flash(f'Erro ao adicionar despesa: {e}', 'danger')
            if conn: conn.rollback()
        
        finally:
            if cur: cur.close()
            if conn: conn.close()
            
    return render_template('add_expense.html')

@app.route('/add_income', methods=['GET','POST'])
@login_required # MUDANÇA: Adicionado wrapper
def add_income():
    if request.method == 'POST':
        desc = request.form['description']
        amount = float(request.form['amount'])
        date = request.form['date'] or datetime.now().strftime('%Y-%m-%d')
        owner = session['user']
        
        conn = None
        cur = None
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            # MUDANÇA: %s
            cur.execute('INSERT INTO incomes (description, amount, date, owner) VALUES (%s,%s,%s,%s)', 
                        (desc, amount, date, owner))
            conn.commit()
            flash('Entrada adicionada ao caixa.', 'success')
            return redirect(url_for('dashboard'))
        
        except Exception as e:
            flash(f'Erro ao adicionar entrada: {e}', 'danger')
            if conn: conn.rollback()
            
        finally:
            if cur: cur.close()
            if conn: conn.close()
            
    return render_template('add_income.html')

@app.route('/expenses')
@login_required # MUDANÇA: Adicionado wrapper
def expenses():
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT * FROM expenses ORDER BY date DESC')
        rows = cur.fetchall()
        return render_template('expenses.html', rows=rows)
    
    except Exception as e:
        flash(f'Erro ao carregar despesas: {e}', 'danger')
        return redirect(url_for('dashboard'))
    
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route('/toggle_paid/<int:exp_id>', methods=['POST'])
@login_required # MUDANÇA: Adicionado wrapper
def toggle_paid(exp_id):
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT paid FROM expenses WHERE id = %s', (exp_id,))
        r = cur.fetchone()
        
        if r:
            new = 0 if r['paid'] == 1 else 1
            cur.execute('UPDATE expenses SET paid = %s WHERE id = %s', (new, exp_id))
            conn.commit()
            
    except Exception as e:
        flash(f'Erro ao atualizar despesa: {e}', 'danger')
        if conn: conn.rollback()
        
    finally:
        if cur: cur.close()
        if conn: conn.close()
        
    return redirect(url_for('expenses'))

@app.route('/delete/<int:exp_id>', methods=['POST'])
@login_required # MUDANÇA: Adicionado wrapper
def delete_expense(exp_id):
    conn = None
    cur = None
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute('DELETE FROM expenses WHERE id = %s', (exp_id,))
        conn.commit()
        flash('Despesa removida.', 'info')
        
    except Exception as e:
        flash(f'Erro ao deletar despesa: {e}', 'danger')
        if conn: conn.rollback()
        
    finally:
        if cur: cur.close()
        if conn: conn.close()
        
    return redirect(url_for('expenses'))

if __name__ == '__main__':
    # MUDANÇA: Configurado para rodar no Render (ou localmente)
    port = int(os.environ.get("PORT", 5000))
    # debug=False é crucial para produção!
    app.run(host='0.0.0.0', port=port, debug=False)
