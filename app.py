from flask import Flask, render_template, request, session, redirect, url_for, flash
from decimal import Decimal, InvalidOperation
import sqlite3
import secrets
import click
import os

DATABASE_FILE = 'banking_app.db'

app = Flask(__name__, template_folder=os.path.abspath('templates'))
app.secret_key = secrets.token_bytes(32)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' in session:
        if 'is_admin' in session and session['is_admin']:
            conn = get_db_connection()
            user = conn.execute('SELECT username, balance FROM admin_users WHERE username = ?', (session['username'],)).fetchone()
            conn.close()
            if user:
                return render_template('home.html', username=user['username'], balance=user['balance'], is_admin=True)
            else:
                return redirect(url_for('login'))
        else:
            conn = get_db_connection()
            user = conn.execute('SELECT username, balance, is_banned FROM users WHERE username = ?', (session['username'],)).fetchone()
            conn.close()
            if user:
                return render_template('home.html', username=user['username'], balance=user['balance'], is_banned=user['is_banned'])
            else:
                return redirect(url_for('login'))
    else:
        return render_template('login.html')

    
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template('admin_login.html')
    else:
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM admin_users WHERE username = ? AND password = ?', (username, password))
        admin_user = cursor.fetchone()
        conn.close()

        if admin_user:
            session['username'] = username
            session['is_admin'] = True
            return redirect(url_for('admin_panel'))
        else:
            flash('Invalid admin credentials', 'error')
            return redirect(url_for('admin_login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user[2] == password:
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    if 'is_admin' in session:
        session.pop('is_admin',None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    else:
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('register'))

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()

@app.route('/profile')
def view_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    if 'is_admin' in session and session['is_admin']:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM admin_users WHERE username = ?', (session['username'],)).fetchone()
        conn.close()
        
        if user:
            return render_template('profile.html', user=user)
        else:
            flash('Admin not found', 'error')
            return redirect(url_for('index'))
    else:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (session['username'],)).fetchone()
        conn.close()
        
        if user:
            return render_template('profile.html', user=user)
        else:
            flash('User not found', 'error')
            return redirect(url_for('index'))

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (session['username'],)).fetchone()
        conn.close()
        return render_template('update_profile.html', user=user)
    else:

        update_data = dict(request.form)

        if 'is_admin' in session and session['is_admin']:
            update_query = "UPDATE admin_users SET " + ", ".join([f"{key} = ?" for key in update_data.keys()]) + " WHERE username = ?"
        else:
            update_query = "UPDATE users SET " + ", ".join([f"{key} = ?" for key in update_data.keys()]) + " WHERE username = ?"

        update_values = tuple(update_data.values()) + (session['username'],)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(update_query, update_values)
        conn.commit()
        conn.close()
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('view_profile'))
    
@app.route('/donation_feed')
def donation_feed():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    active_requests = conn.execute('SELECT * FROM donation_requests WHERE status = "active" ORDER BY created_at DESC').fetchall()
    completed_requests = conn.execute('SELECT * FROM donation_requests WHERE status = "completed" ORDER BY created_at DESC').fetchall()
    comments = conn.execute('SELECT * FROM comments ORDER BY created_at DESC').fetchall()
    
    conn.close()
    
    return render_template('donation_feed.html', active_requests=active_requests, completed_requests=completed_requests, comments=comments)

@app.route('/create_donation_request', methods=['GET', 'POST'])
def create_donation_request():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT is_banned FROM users WHERE username = ?', (session['username'],)).fetchone()
    conn.close()
    
    if user['is_banned']:
        flash('You are banned and cannot create donation requests.', 'error')
        return redirect(url_for('donation_feed'))
    
    if request.method == 'GET':
        return render_template('create_donation_request.html')
    else:
        amount = float(request.form['amount'])
        description = request.form['description']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO donation_requests (username, amount, description) VALUES (?, ?, ?)',
                       (session['username'], amount, description))
        conn.commit()
        conn.close()
        
        flash('Donation request created successfully', 'success')
        return redirect(url_for('donation_feed'))

@app.route('/donate/<int:request_id>', methods=['POST'])
def donate(request_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    user = conn.execute('SELECT is_banned FROM users WHERE username = ?', (session['username'],)).fetchone()
    conn.close()
    
    if user['is_banned']:
        flash('You are banned and cannot donate.', 'error')
        return redirect(url_for('donation_feed'))
    try:
        amount = Decimal(request.form['amount']).quantize(Decimal('.01'))
        if amount <= 0:
            raise ValueError("Amount must be positive")
    except (InvalidOperation, ValueError):
        flash('Invalid donation amount', 'error')
        return redirect(url_for('donation_feed'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:

        cursor.execute('BEGIN TRANSACTION')

        donation_request = cursor.execute('SELECT username, amount, status FROM donation_requests WHERE id = ?', (request_id,)).fetchone()
        if not donation_request or donation_request['status'] != 'active':
            raise ValueError("Invalid or inactive donation request")
        
        donor = cursor.execute('SELECT balance FROM users WHERE username = ?', (session['username'],)).fetchone()
        if not donor or Decimal(donor['balance']) < amount:
            raise ValueError("Insufficient balance")
        
        if amount > Decimal(donation_request['amount']):
            raise ValueError("Donation amount exceeds the requested amount")
        
        cursor.execute('UPDATE users SET balance = balance - ? WHERE username = ?', (str(amount), session['username']))
        
        cursor.execute('UPDATE users SET balance = balance + ? WHERE username = ?', (str(amount), donation_request['username']))
        
        new_amount = max(0, Decimal(donation_request['amount']) - amount)
        cursor.execute('UPDATE donation_requests SET amount = ? WHERE id = ?', (str(new_amount), request_id))
        
        if new_amount == 0:
            cursor.execute('UPDATE donation_requests SET status = "completed" WHERE id = ?', (request_id,))
        
        cursor.execute('COMMIT')
        
        flash('Donation successful', 'success')
    
    except ValueError as e:
        cursor.execute('ROLLBACK')
        flash(str(e), 'error')
    except Exception as e:
        cursor.execute('ROLLBACK')
        flash('An error occurred during the donation process', 'error')
        print(f"Unexpected error in donate: {e}")
    finally:
        conn.close()
    
    return redirect(url_for('donation_feed'))

def is_admin():
    return session.get('is_admin', False)

@app.route('/admin')
def admin_panel():
    if not is_admin():
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    
    return render_template('admin_panel.html', users=users)

@app.route('/admin/ban/<string:username>', methods=['POST'])
def ban_user(username):
    if not is_admin():
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 , balance = 0 WHERE username = ?', (username,))
    cursor.execute('DELETE FROM donation_requests WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    
    flash(f'User {username} has been banned and their donation requests have been deleted.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/admin/unban/<string:username>', methods=['POST'])
def unban_user(username):
    if not is_admin():
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    
    flash(f'User {username} has been unbanned.', 'success')
    return redirect(url_for('admin_panel'))

@app.route('/add_comment/<int:request_id>', methods=['POST'])
def add_comment(request_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    content = request.form['content']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO comments (donation_request_id, username, content) VALUES (?, ?, ?)',
                   (request_id, session['username'], content))
    conn.commit()
    conn.close()
    
    flash('Comment added successfully', 'success')
    return redirect(url_for('donation_feed'))

@app.route('/edit_comment/<int:comment_id>', methods=['GET', 'POST'])
def edit_comment(comment_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    
    if not comment:
        flash('Comment not found!', 'error')
        return redirect(url_for('donation_feed'))
    
    if request.method == 'POST':
        new_content = request.form['content']
        cursor = conn.cursor()
        cursor.execute('UPDATE comments SET content = ? WHERE id = ?', (new_content, comment_id))
        conn.commit()
        flash('Comment updated successfully', 'success')
        return redirect(url_for('donation_feed'))
    
    conn.close()
    return render_template('edit_comment.html', comment=comment)

@app.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    
    if not comment:
        flash('Comment not found!', 'error')
        return redirect(url_for('donation_feed'))
    
    cursor = conn.cursor()
    cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.commit()
    conn.close()
    
    flash('Comment deleted successfully', 'success')
    return redirect(url_for('donation_feed'))

def init_db():
    conn = get_db_connection()
    with app.open_resource('schema.sql', mode='r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

@app.cli.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

if __name__ == '__main__':
    app.run(debug=True)