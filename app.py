from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
import os
import secrets
from datetime import datetime

APP_SECRET = os.environ.get('APP_SECRET', 'troque_esta_chave')
DB = os.environ.get('DB_PATH', 'studio_v2.db')

from flask import Flask
app = Flask(__name__)

app.config['SECRET_KEY'] = APP_SECRET

# Configuração do Flask-Mail (use variáveis de ambiente para credenciais reais)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

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
        conn = get_db()
        cur = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cur.fetchone()
        conn.close()
        if user and user['registered'] == 1 and check_password_hash(user['password_hash'], password):
            session['user'] = username
            flash('Logado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        flash('Usuário/senha incorretos ou usuário não registrado.', 'danger')
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
        conn = get_db()
        cur = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cur.fetchone()
        if not user:
            flash('Nome de usuário não permitido.', 'danger')
            conn.close()
            return redirect(url_for('register'))
        if user['registered'] == 1:
            flash('Usuário já registrado. Faça login ou use esqueci a senha.', 'warning')
            conn.close()
            return redirect(url_for('login'))
        pw_hash = generate_password_hash(password)
        conn.execute('UPDATE users SET password_hash = ?, email = ?, registered = 1 WHERE username = ?', (pw_hash, email, username))
        conn.commit()
        conn.close()
        flash('Cadastro realizado! Agora faça login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        username = request.form['username'].strip()
        conn = get_db()
        cur = conn.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cur.fetchone()
        if not user or not user['email']:
            flash('Usuário não encontrado ou sem e-mail cadastrado.', 'danger')
            conn.close()
            return redirect(url_for('forgot'))
        temp_pw = secrets.token_urlsafe(8)
        pw_hash = generate_password_hash(temp_pw)
        conn.execute('UPDATE users SET password_hash = ? WHERE username = ?', (pw_hash, username))
        conn.commit()
        conn.close()
        try:
            msg = Message('Recuperação de senha - Studio', recipients=[user['email']])
            msg.body = f"Olá {username},\n\nRecebemos um pedido de recuperação de senha. Sua senha temporária é: {temp_pw}\nPor favor, entre e altere sua senha depois.\n\n— Equipe do Studio"
            mail.send(msg)
            flash('E-mail enviado com senha temporária.', 'info')
        except Exception as e:
            print('Erro enviando e-mail:', e)
            flash('Falha ao enviar e-mail. Verifique a configuração do servidor de e-mail.', 'danger')
        return redirect(url_for('login'))
    return render_template('forgot.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('user'):
        return redirect(url_for('login'))
    user = session['user']
    conn = get_db()
    # totals
    cur = conn.execute('SELECT IFNULL(SUM(amount),0) as total FROM incomes')
    total_income = cur.fetchone()['total']
    cur = conn.execute('SELECT IFNULL(SUM(amount),0) as total FROM expenses WHERE paid = 1')
    total_spent = cur.fetchone()['total']
    cur = conn.execute('SELECT IFNULL(SUM(amount),0) as total FROM expenses WHERE paid = 0')
    total_pending = cur.fetchone()['total']
    total_available = total_income - total_spent
    # recent expenses
    cur = conn.execute('SELECT * FROM expenses ORDER BY date DESC LIMIT 10')
    recent = cur.fetchall()
    conn.close()
    return render_template('dashboard.html', user=user, total_income=total_income, total_spent=total_spent, total_pending=total_pending, total_available=total_available, recent=recent)

@app.route('/add', methods=['GET','POST'], endpoint='add')
def add_expense():

    if not session.get('user'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        desc = request.form['description']
        amount = float(request.form['amount'])
        date = request.form['date'] or datetime.now().strftime('%Y-%m-%d')
        urgency = int(request.form.get('urgency','0'))
        owner = session['user']
        conn = get_db()
        conn.execute('INSERT INTO expenses (description, amount, date, urgency, owner) VALUES (?,?,?,?,?)', (desc, amount, date, urgency, owner))
        conn.commit()
        conn.close()
        flash('Despesa adicionada.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html')

@app.route('/add_income', methods=['GET','POST'])
def add_income():
    if not session.get('user'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        desc = request.form['description']
        amount = float(request.form['amount'])
        date = request.form['date'] or datetime.now().strftime('%Y-%m-%d')
        owner = session['user']
        conn = get_db()
        conn.execute('INSERT INTO incomes (description, amount, date, owner) VALUES (?,?,?,?)', (desc, amount, date, owner))
        conn.commit()
        conn.close()
        flash('Entrada adicionada ao caixa.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_income.html')

@app.route('/expenses')
def expenses():
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.execute('SELECT * FROM expenses ORDER BY date DESC')
    rows = cur.fetchall()
    conn.close()
    return render_template('expenses.html', rows=rows)

@app.route('/toggle_paid/<int:exp_id>', methods=['POST'])
def toggle_paid(exp_id):
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    cur = conn.execute('SELECT paid FROM expenses WHERE id = ?', (exp_id,))
    r = cur.fetchone()
    if r:
        new = 0 if r['paid'] == 1 else 1
        conn.execute('UPDATE expenses SET paid = ? WHERE id = ?', (new, exp_id))
        conn.commit()
    conn.close()
    return redirect(url_for('expenses'))

@app.route('/delete/<int:exp_id>', methods=['POST'])
def delete_expense(exp_id):
    if not session.get('user'):
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute('DELETE FROM expenses WHERE id = ?', (exp_id,))
    conn.commit()
    conn.close()
    flash('Despesa removida.', 'info')
    return redirect(url_for('expenses'))

if __name__ == '__main__':
    app.run(debug=True)
