import os
import secrets
import re
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, session, flash, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)
)

DATABASE = 'database.db'

# =============================================================================
# SECURITY HELPERS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in.', 'warning')
                return redirect('/login')
            if session.get('role') not in roles:
                flash('Insufficient permissions.', 'danger')
                return redirect('/dashboard')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def generate_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_urlsafe(32)
    return session['csrf_token']

app.jinja_env.globals['csrf_token'] = generate_csrf_token

def validate_csrf():
    token = request.form.get('csrf_token')
    if not token or token != session.get('csrf_token'):
        abort(403)

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    if not phone:
        return True
    pattern = r'^[+\d\s\-\(\)]{7,20}$'
    return re.match(pattern, phone) is not None

def sanitize_input(text):
    if not text:
        return text
    return text.strip()

# =============================================================================
# DATABASE
# =============================================================================

import sqlite3

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Employee' CHECK(role IN ('Admin', 'Manager', 'Employee')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'New' CHECK(status IN ('New', 'Contacted', 'Qualified', 'Lost')),
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount INTEGER NOT NULL,
            stage TEXT DEFAULT 'Prospect' CHECK(stage IN ('Prospect', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost')),
            lead_id INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE SET NULL,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER DEFAULT 0 CHECK(stock >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            valid_until TEXT NOT NULL,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'Unpaid' CHECK(status IN ('Paid', 'Unpaid', 'Overdue')),
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            priority TEXT DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High')),
            status TEXT DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Completed')),
            assigned_to INTEGER,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(assigned_to) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            uploaded_by INTEGER,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE SET NULL
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')

    conn.commit()
    conn.close()

init_db()

def log_action(action):
    conn = get_db()
    conn.execute('INSERT INTO audit_logs (user_id, action) VALUES (?, ?)', (session.get('user_id'), action))
    conn.commit()
    conn.close()

# =============================================================================
# AUTHENTICATION
# =============================================================================

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect('/dashboard')
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '')
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect('/login')
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            conn = get_db()
            conn.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
            conn.commit()
            conn.close()
            log_action(f"User {user['username']} logged in")
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect('/dashboard')
        flash('Invalid email or password.', 'danger')
        return redirect('/login')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect('/dashboard')
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', ''))
        email = sanitize_input(request.form.get('email', ''))
        password = request.form.get('password', '')
        role = request.form.get('role', 'Employee')
        if not username or len(username) < 2:
            flash('Username must be at least 2 characters.', 'danger')
            return redirect('/register')
        if not validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return redirect('/register')
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return redirect('/register')
        if role not in ('Admin', 'Manager', 'Employee'):
            role = 'Employee'
        password_hash = generate_password_hash(password)
        conn = get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)',
                (username, email, password_hash, role)
            )
            conn.commit()
            user_id = cursor.lastrowid
            log_action(f"New user registered: {username} ({role})")
            flash('Account created successfully! Please log in.', 'success')
            return redirect('/login')
        except sqlite3.IntegrityError:
            flash('Email address is already registered.', 'danger')
            return redirect('/register')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    log_action(f"User {session.get('username')} logged out")
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect('/login')

# =============================================================================
# DASHBOARD
# =============================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    stats = {
        'total_leads': conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0],
        'total_deals': conn.execute('SELECT COUNT(*) FROM deals').fetchone()[0],
        'total_tasks': conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0],
        'completed_tasks': conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'").fetchone()[0],
        'total_revenue': conn.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'Paid'").fetchone()[0],
        'outstanding': conn.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'Unpaid'").fetchone()[0],
        'pipeline_value': conn.execute("SELECT COALESCE(SUM(amount), 0) FROM deals WHERE stage != 'Closed Lost'").fetchone()[0],
        'low_stock': conn.execute('SELECT COUNT(*) FROM products WHERE stock < 5').fetchone()[0],
    }
    recent_leads = conn.execute('SELECT * FROM leads ORDER BY created_at DESC LIMIT 5').fetchall()
    recent_tasks = conn.execute('SELECT t.*, u.username as assignee FROM tasks t LEFT JOIN users u ON t.assigned_to = u.id ORDER BY t.created_at DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('dashboard.html', stats=stats, recent_leads=recent_leads,
                          recent_tasks=recent_tasks, username=session['username'],
                          role=session['role'])

# =============================================================================
# LEADS
# =============================================================================

@app.route('/leads')
@login_required
def view_leads():
    conn = get_db()
    leads = conn.execute('SELECT * FROM leads ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('leads.html', leads=leads)

@app.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    if request.method == 'POST':
        validate_csrf()
        name = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', ''))
        phone = sanitize_input(request.form.get('phone', ''))
        if not name:
            flash('Name is required.', 'danger')
            return redirect('/leads/add')
        if email and not validate_email(email):
            flash('Please enter a valid email.', 'danger')
            return redirect('/leads/add')
        if phone and not validate_phone(phone):
            flash('Please enter a valid phone number.', 'danger')
            return redirect('/leads/add')
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO leads (name, email, phone, created_by) VALUES (?, ?, ?, ?)',
            (name, email, phone, session['user_id'])
        )
        conn.commit()
        lead_id = cursor.lastrowid
        conn.close()
        log_action(f"Created lead #{lead_id}: {name}")
        flash('Lead created successfully!', 'success')
        return redirect('/leads')
    return render_template('add_lead.html')

@app.route('/leads/view/<int:id>')
@login_required
def view_lead_profile(id):
    conn = get_db()
    lead = conn.execute('SELECT * FROM leads WHERE id = ?', (id,)).fetchone()
    deals = conn.execute('SELECT * FROM deals WHERE lead_id = ?', (id,)).fetchall()
    conn.close()
    if not lead:
        abort(404)
    return render_template('view_lead.html', lead=lead, deals=deals)

@app.route('/leads/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    conn = get_db()
    lead = conn.execute('SELECT * FROM leads WHERE id = ?', (id,)).fetchone()
    if not lead:
        conn.close()
        abort(404)
    if request.method == 'POST':
        validate_csrf()
        name = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', ''))
        phone = sanitize_input(request.form.get('phone', ''))
        if not name:
            flash('Name is required.', 'danger')
            return redirect(f'/leads/edit/{id}')
        if email and not validate_email(email):
            flash('Please enter a valid email.', 'danger')
            return redirect(f'/leads/edit/{id}')
        conn.execute(
            'UPDATE leads SET name=?, email=?, phone=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (name, email, phone, id)
        )
        conn.commit()
        conn.close()
        log_action(f"Updated lead #{id}: {name}")
        flash('Lead updated successfully!', 'success')
        return redirect('/leads')
    conn.close()
    return render_template('edit_lead.html', lead=lead)

@app.route('/leads/status/<int:id>', methods=['GET', 'POST'])
@login_required
def change_lead_status(id):
    conn = get_db()
    lead = conn.execute('SELECT * FROM leads WHERE id = ?', (id,)).fetchone()
    if not lead:
        conn.close()
        abort(404)
    if request.method == 'POST':
        validate_csrf()
        status = request.form.get('status', 'New')
        if status not in ('New', 'Contacted', 'Qualified', 'Lost'):
            flash('Invalid status.', 'danger')
            return redirect(f'/leads/status/{id}')
        conn.execute('UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (status, id))
        conn.commit()
        conn.close()
        log_action(f"Changed lead #{id} status to {status}")
        flash('Status updated!', 'success')
        return redirect('/leads')
    conn.close()
    return render_template('status_lead.html', lead=lead)

@app.route('/leads/delete/<int:id>', methods=['POST'])
@login_required
def purge_lead_entry(id):
    validate_csrf()
    conn = get_db()
    lead = conn.execute('SELECT * FROM leads WHERE id = ?', (id,)).fetchone()
    if not lead:
        conn.close()
        abort(404)
    conn.execute('DELETE FROM leads WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    log_action(f"Deleted lead #{id}: {lead['name']}")
    flash('Lead deleted.', 'info')
    return redirect('/leads')

# =============================================================================
# SALES PIPELINE
# =============================================================================

@app.route('/pipeline')
@login_required
def deal_pipeline():
    conn = get_db()
    deals = conn.execute('SELECT d.*, l.name as lead_name FROM deals d LEFT JOIN leads l ON d.lead_id = l.id ORDER BY d.created_at DESC').fetchall()
    conn.close()
    return render_template('pipeline.html', deals=deals)

@app.route('/deals/add', methods=['GET', 'POST'])
@login_required
def add_deal_entry():
    conn = get_db()
    leads = conn.execute('SELECT id, name FROM leads ORDER BY name').fetchall()
    if request.method == 'POST':
        validate_csrf()
        title = sanitize_input(request.form.get('title', ''))
        amount_str = request.form.get('amount', '0')
        lead_id = request.form.get('lead_id')
        if not title:
            flash('Deal title is required.', 'danger')
            return redirect('/deals/add')
        try:
            amount = int(float(amount_str) * 100)
            if amount < 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid amount.', 'danger')
            return redirect('/deals/add')
        lead_id = int(lead_id) if lead_id else None
        cursor = conn.execute(
            'INSERT INTO deals (title, amount, lead_id, created_by) VALUES (?, ?, ?, ?)',
            (title, amount, lead_id, session['user_id'])
        )
        conn.commit()
        deal_id = cursor.lastrowid
        conn.close()
        log_action(f"Created deal #{deal_id}: {title}")
        flash('Deal added to pipeline!', 'success')
        return redirect('/pipeline')
    conn.close()
    return render_template('add_deal.html', leads=leads)

@app.route('/deals/move/<int:id>', methods=['GET', 'POST'])
@login_required
def move_deal_stage(id):
    conn = get_db()
    deal = conn.execute('SELECT * FROM deals WHERE id = ?', (id,)).fetchone()
    if not deal:
        conn.close()
        abort(404)
    if request.method == 'POST':
        validate_csrf()
        stage = request.form.get('stage', 'Prospect')
        if stage not in ('Prospect', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost'):
            flash('Invalid stage.', 'danger')
            return redirect(f'/deals/move/{id}')
        conn.execute('UPDATE deals SET stage = ? WHERE id = ?', (stage, id))
        conn.commit()
        conn.close()
        log_action(f"Moved deal #{id} to {stage}")
        flash('Deal stage updated!', 'success')
        return redirect('/pipeline')
    conn.close()
    return render_template('move_deal.html', deal=deal)

@app.route('/deals/delete/<int:id>', methods=['POST'])
@login_required
def drop_deal_record(id):
    validate_csrf()
    conn = get_db()
    deal = conn.execute('SELECT * FROM deals WHERE id = ?', (id,)).fetchone()
    if not deal:
        conn.close()
        abort(404)
    conn.execute('DELETE FROM deals WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    log_action(f"Deleted deal #{id}: {deal['title']}")
    flash('Deal removed.', 'info')
    return redirect('/pipeline')

# =============================================================================
# INVENTORY
# =============================================================================

@app.route('/inventory')
@login_required
def product_catalog():
    conn = get_db()
    items = conn.execute('SELECT * FROM products ORDER BY name').fetchall()
    conn.close()
    return render_template('inventory.html', items=items)

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def append_product_catalog():
    if request.method == 'POST':
        validate_csrf()
        name = sanitize_input(request.form.get('name', ''))
        sku = sanitize_input(request.form.get('sku', ''))
        price_str = request.form.get('price', '0')
        if not name or not sku:
            flash('Product name and SKU are required.', 'danger')
            return redirect('/inventory/add')
        try:
            price = int(float(price_str) * 100)
            if price < 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid price.', 'danger')
            return redirect('/inventory/add')
        conn = get_db()
        try:
            cursor = conn.execute(
                'INSERT INTO products (name, sku, price) VALUES (?, ?, ?)',
                (name, sku, price)
            )
            conn.commit()
            product_id = cursor.lastrowid
            conn.close()
            log_action(f"Created product #{product_id}: {name}")
            flash('Product added to catalog!', 'success')
            return redirect('/inventory')
        except sqlite3.IntegrityError:
            conn.close()
            flash('SKU already exists.', 'danger')
            return redirect('/inventory/add')
    return render_template('add_product.html')

@app.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def alter_product_details(id):
    conn = get_db()
    item = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    if not item:
        conn.close()
        abort(404)
    if request.method == 'POST':
        validate_csrf()
        name = sanitize_input(request.form.get('name', ''))
        price_str = request.form.get('price', '0')
        if not name:
            flash('Product name is required.', 'danger')
            return redirect(f'/inventory/edit/{id}')
        try:
            price = int(float(price_str) * 100)
            if price < 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid price.', 'danger')
            return redirect(f'/inventory/edit/{id}')
        conn.execute('UPDATE products SET name=?, price=? WHERE id=?', (name, price, id))
        conn.commit()
        conn.close()
        log_action(f"Updated product #{id}: {name}")
        flash('Product updated!', 'success')
        return redirect('/inventory')
    conn.close()
    return render_template('edit_product.html', item=item)

@app.route('/inventory/stock', methods=['GET', 'POST'])
@login_required
def adjust_stock_limits():
    conn = get_db()
    if request.method == 'POST':
        validate_csrf()
        pid = request.form.get('product_id')
        qty_str = request.form.get('qty', '0')
        try:
            qty = int(qty_str)
            pid = int(pid)
        except ValueError:
            flash('Invalid input.', 'danger')
            return redirect('/inventory/stock')
        product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
        if not product:
            conn.close()
            flash('Product not found.', 'danger')
            return redirect('/inventory/stock')
        new_stock = product['stock'] + qty
        if new_stock < 0:
            conn.close()
            flash(f"Cannot reduce stock below zero. Current: {product['stock']}, Requested: {qty}", 'danger')
            return redirect('/inventory/stock')
        conn.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock, pid))
        conn.commit()
        conn.close()
        action = 'restocked' if qty > 0 else 'deducted stock from'
        log_action(f"{action} product #{pid}: {abs(qty)} units")
        flash(f"Stock updated! New quantity: {new_stock}", 'success')
        return redirect('/inventory')
    items = conn.execute('SELECT id, name, stock FROM products ORDER BY name').fetchall()
    conn.close()
    return render_template('stocks.html', items=items)

# =============================================================================
# QUOTES
# =============================================================================

@app.route('/quotes')
@login_required
def sales_quotes_board():
    conn = get_db()
    quotes = conn.execute('SELECT q.*, u.username as creator FROM quotes q LEFT JOIN users u ON q.created_by = u.id ORDER BY q.created_at DESC').fetchall()
    conn.close()
    return render_template('quotes.html', quotes=quotes)

@app.route('/quotes/create', methods=['GET', 'POST'])
@login_required
def mint_new_quote():
    if request.method == 'POST':
        validate_csrf()
        client = sanitize_input(request.form.get('client', ''))
        amount_str = request.form.get('amount', '0')
        validity = request.form.get('validity', '')
        if not client:
            flash('Client name is required.', 'danger')
            return redirect('/quotes/create')
        try:
            amount = int(float(amount_str) * 100)
            if amount < 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid amount.', 'danger')
            return redirect('/quotes/create')
        if not validity:
            flash('Validity date is required.', 'danger')
            return redirect('/quotes/create')
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO quotes (client_name, amount, valid_until, created_by) VALUES (?, ?, ?, ?)',
            (client, amount, validity, session['user_id'])
        )
        conn.commit()
        quote_id = cursor.lastrowid
        conn.close()
        log_action(f"Created quote #{quote_id} for {client}")
        flash('Quote created!', 'success')
        return redirect('/quotes')
    return render_template('create_quote.html')

@app.route('/quotes/view/<int:id>')
@login_required
def export_quote_view(id):
    conn = get_db()
    quote = conn.execute('SELECT * FROM quotes WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not quote:
        abort(404)
    return render_template('view_quote.html', quote=quote)

# =============================================================================
# INVOICES
# =============================================================================

@app.route('/invoices')
@login_required
def invoices_ledger():
    conn = get_db()
    invoices = conn.execute('SELECT i.*, u.username as creator FROM invoices i LEFT JOIN users u ON i.created_by = u.id ORDER BY i.created_at DESC').fetchall()
    conn.close()
    return render_template('invoice.html', invoices=invoices)

@app.route('/invoices/create', methods=['GET', 'POST'])
@login_required
def generate_invoice_receipt():
    if request.method == 'POST':
        validate_csrf()
        client = sanitize_input(request.form.get('client', ''))
        amount_str = request.form.get('amount', '0')
        if not client:
            flash('Client name is required.', 'danger')
            return redirect('/invoices/create')
        try:
            amount = int(float(amount_str) * 100)
            if amount < 0:
                raise ValueError
        except ValueError:
            flash('Please enter a valid amount.', 'danger')
            return redirect('/invoices/create')
        conn = get_db()
        cursor = conn.execute(
            'INSERT INTO invoices (client_name, amount, created_by) VALUES (?, ?, ?)',
            (client, amount, session['user_id'])
        )
        conn.commit()
        inv_id = cursor.lastrowid
        conn.close()
        log_action(f"Created invoice #{inv_id} for {client}")
        flash('Invoice created!', 'success')
        return redirect('/invoices')
    return render_template('create_invoice.html')

@app.route('/invoices/view/<int:id>')
@login_required
def billing_invoice_view(id):
    conn = get_db()
    inv = conn.execute('SELECT * FROM invoices WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not inv:
        abort(404)
    return render_template('view_invoice.html', inv=inv)

@app.route('/invoices/pay/<int:id>', methods=['GET', 'POST'])
@login_required
def intercept_payment_gateway(id):
    conn = get_db()
    inv = conn.execute('SELECT * FROM invoices WHERE id = ?', (id,)).fetchone()
    if not inv:
        conn.close()
        abort(404)
    if inv['status'] == 'Paid':
        conn.close()
        flash('Invoice is already paid.', 'info')
        return redirect('/invoices')
    if request.method == 'POST':
        validate_csrf()
        conn.execute("UPDATE invoices SET status = 'Paid', paid_at = CURRENT_TIMESTAMP WHERE id = ?", (id,))
        conn.commit()
        conn.close()
        log_action(f"Invoice #{id} marked as Paid")
        flash('Payment processed successfully!', 'success')
        return redirect('/invoices')
    conn.close()
    return render_template('payment_gate.html', id=id)

@app.route('/finance/audit')
@login_required
def historic_payments_audit():
    conn = get_db()
    records = conn.execute("SELECT i.*, u.username as creator FROM invoices i LEFT JOIN users u ON i.created_by = u.id WHERE i.status = 'Paid' ORDER BY i.paid_at DESC").fetchall()
    conn.close()
    return render_template('payments_log.html', records=records)

@app.route('/finance/summary')
@login_required
def billing_summary_log():
    conn = get_db()
    total_paid = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'Paid'").fetchone()[0]
    total_unpaid = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'Unpaid'").fetchone()[0]
    total_overdue = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM invoices WHERE status = 'Overdue'").fetchone()[0]
    conn.close()
    return render_template('billing_summary.html', total_paid=total_paid, total_unpaid=total_unpaid, total_overdue=total_overdue)

# =============================================================================
# TASKS
# =============================================================================

@app.route('/tasks')
@login_required
def view_tasks_board():
    conn = get_db()
    tasks = conn.execute('SELECT t.*, u.username as assignee_name FROM tasks t LEFT JOIN users u ON t.assigned_to = u.id ORDER BY CASE t.priority WHEN "High" THEN 1 WHEN "Medium" THEN 2 ELSE 3 END, t.due_date').fetchall()
    conn.close()
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/create', methods=['GET', 'POST'])
@login_required
def schedule_new_task():
    conn = get_db()
    users = conn.execute('SELECT id, username FROM users ORDER BY username').fetchall()
    if request.method == 'POST':
        validate_csrf()
        title = sanitize_input(request.form.get('title', ''))
        description = sanitize_input(request.form.get('description', ''))
        due_date = request.form.get('due_date', '')
        priority = request.form.get('priority', 'Medium')
        assigned_to = request.form.get('assigned_to')
        if not title:
            flash('Task title is required.', 'danger')
            return redirect('/tasks/create')
        if priority not in ('Low', 'Medium', 'High'):
            priority = 'Medium'
        assigned_to = int(assigned_to) if assigned_to else session['user_id']
        cursor = conn.execute(
            'INSERT INTO tasks (title, description, due_date, priority, assigned_to, created_by) VALUES (?, ?, ?, ?, ?, ?)',
            (title, description, due_date, priority, assigned_to, session['user_id'])
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        log_action(f"Created task #{task_id}: {title}")
        flash('Task scheduled!', 'success')
        return redirect('/tasks')
    conn.close()
    return render_template('create_task.html', users=users)

@app.route('/tasks/view/<int:id>')
@login_required
def drill_task_details(id):
    conn = get_db()
    task = conn.execute('SELECT t.*, u.username as assignee_name, c.username as creator_name FROM tasks t LEFT JOIN users u ON t.assigned_to = u.id LEFT JOIN users c ON t.created_by = c.id WHERE t.id = ?', (id,)).fetchone()
    conn.close()
    if not task:
        abort(404)
    return render_template('view_task.html', task=task)

@app.route('/tasks/status/<int:id>', methods=['GET', 'POST'])
@login_required
def update_task_lifecycle(id):
    conn = get_db()
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (id,)).fetchone()
    if not task:
        conn.close()
        abort(404)
    if request.method == 'POST':
        validate_csrf()
        status = request.form.get('status', 'Pending')
        if status not in ('Pending', 'In Progress', 'Completed'):
            flash('Invalid status.', 'danger')
            return redirect(f'/tasks/status/{id}')
        conn.execute('UPDATE tasks SET status = ? WHERE id = ?', (status, id))
        conn.commit()
        conn.close()
        log_action(f"Updated task #{id} status to {status}")
        flash('Task status updated!', 'success')
        return redirect('/tasks')
    conn.close()
    return render_template('edit_task_status.html', task=task)

@app.route('/tasks/delete/<int:id>', methods=['POST'])
@login_required
def drop_task_record(id):
    validate_csrf()
    conn = get_db()
    task = conn.execute('SELECT * FROM tasks WHERE id = ?', (id,)).fetchone()
    if not task:
        conn.close()
        abort(404)
    conn.execute('DELETE FROM tasks WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    log_action(f"Deleted task #{id}: {task['title']}")
    flash('Task deleted.', 'info')
    return redirect('/tasks')

@app.route('/tasks/archive')
@login_required
def tasks_archive():
    conn = get_db()
    tasks = conn.execute("SELECT t.*, u.username as assignee_name FROM tasks t LEFT JOIN users u ON t.assigned_to = u.id WHERE t.status = 'Completed' ORDER BY t.created_at DESC").fetchall()
    conn.close()
    return render_template('tasks_archive.html', tasks=tasks)

# =============================================================================
# CHAT & MESSAGING
# =============================================================================

@app.route('/chat')
@login_required
def team_chat():
    conn = get_db()
    messages = conn.execute('SELECT m.*, u.username as sender_name FROM messages m LEFT JOIN users u ON m.sender_id = u.id ORDER BY m.timestamp DESC LIMIT 50').fetchall()
    conn.close()
    return render_template('chat.html', messages=messages)

@app.route('/chat/send', methods=['POST'])
@login_required
def send_chat_msg():
    validate_csrf()
    text = sanitize_input(request.form.get('text', ''))
    if not text:
        flash('Message cannot be empty.', 'warning')
        return redirect('/chat')
    if len(text) > 1000:
        flash('Message too long (max 1000 characters).', 'warning')
        return redirect('/chat')
    conn = get_db()
    conn.execute('INSERT INTO messages (sender_id, text) VALUES (?, ?)', (session['user_id'], text))
    conn.commit()
    conn.close()
    return redirect('/chat')

# =============================================================================
# DOCUMENTS
# =============================================================================

@app.route('/documents')
@login_required
def view_documents():
    conn = get_db()
    docs = conn.execute('SELECT d.*, u.username as uploader FROM documents d LEFT JOIN users u ON d.uploaded_by = u.id ORDER BY d.uploaded_at DESC').fetchall()
    conn.close()
    return render_template('documents.html', docs=docs)

@app.route('/documents/upload', methods=['POST'])
@login_required
def upload_document():
    validate_csrf()
    filename = sanitize_input(request.form.get('filename', ''))
    if not filename:
        flash('Filename is required.', 'danger')
        return redirect('/documents')
    if len(filename) > 255:
        flash('Filename too long.', 'danger')
        return redirect('/documents')
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO documents (filename, uploaded_by) VALUES (?, ?)',
        (filename, session['user_id'])
    )
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    log_action(f"Uploaded document #{doc_id}: {filename}")
    flash('Document uploaded!', 'success')
    return redirect('/documents')

@app.route('/documents/delete/<int:id>', methods=['POST'])
@login_required
def delete_document_record(id):
    validate_csrf()
    conn = get_db()
    doc = conn.execute('SELECT * FROM documents WHERE id = ?', (id,)).fetchone()
    if not doc:
        conn.close()
        abort(404)
    conn.execute('DELETE FROM documents WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    log_action(f"Deleted document #{id}: {doc['filename']}")
    flash('Document deleted.', 'info')
    return redirect('/documents')

# =============================================================================
# ADMIN & SYSTEM
# =============================================================================

@app.route('/system/logs')
@role_required('Admin', 'Manager')
def view_audit_logs():
    conn = get_db()
    logs = conn.execute('SELECT a.*, u.username FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id ORDER BY a.timestamp DESC LIMIT 200').fetchall()
    conn.close()
    return render_template('audit_logs.html', logs=logs)

@app.route('/admin/users')
@role_required('Admin')
def master_user_management_grid():
    conn = get_db()
    all_users = conn.execute('SELECT id, username, email, role, created_at, last_login FROM users ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('admin_users.html', users=all_users)

@app.route('/admin/users/delete/<int:id>', methods=['POST'])
@role_required('Admin')
def core_force_purge_user(id):
    validate_csrf()
    if id == session['user_id']:
        flash('You cannot delete your own account.', 'danger')
        return redirect('/admin/users')
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
    if not user:
        conn.close()
        abort(404)
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    log_action(f"Admin deleted user #{id}: {user['username']}")
    flash('User deleted.', 'info')
    return redirect('/admin/users')

@app.route('/admin/system/flush-cache')
@role_required('Admin')
def system_flush_cache_routine():
    log_action('System cache flushed by admin')
    return render_template('system_message.html', title='Cache Cleared', message='System cache has been cleared successfully.', theme='dark')

@app.route('/system/health')
def engine_runtime_diagnostic_pulse():
    return jsonify({'status': 'healthy', 'engine': 'functional', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/dashboard/announcements')
@login_required
def crm_system_announcements_ticker():
    return render_template('announcement.html')

@app.route('/analytics/conversion-ratio')
@login_required
def calculated_lead_conversion_ratio_panel():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0] or 1
    won = conn.execute("SELECT COUNT(*) FROM deals WHERE stage = 'Closed Won'").fetchone()[0]
    ratio = (won / total) * 100
    conn.close()
    return render_template('metric_display.html', title='Conversion Ratio', value=f'{ratio:.2f}%')

@app.route('/admin/system/backup-trigger')
@role_required('Admin')
def database_file_dump_trigger():
    import shutil
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'database_backup_{timestamp}.db'
    try:
        shutil.copy(DATABASE, backup_name)
        log_action(f"Database backup created: {backup_name}")
        return render_template('system_message.html', title='Backup Complete', message=f'Database backed up to {backup_name}', theme='light')
    except Exception as e:
        return render_template('system_message.html', title='Backup Failed', message=str(e), theme='error')

@app.route('/tasks/efficiency-metric')
@login_required
def team_tasks_efficiency_index():
    conn = get_db()
    done = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'").fetchone()[0]
    total = conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0] or 1
    conn.close()
    return render_template('metric_display.html', title='Task Efficiency', value=f'{done} completed / {total} total ({(done/total*100):.1f}%)')

@app.route('/api/finance/active-ledger')
@login_required
def active_financial_ledger_index_feed():
    conn = get_db()
    rows = conn.execute("SELECT id, amount, status FROM invoices ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify({'financial_ledger_entries': [dict(r) for r in rows]})

@app.route('/api/users/count')
@login_required
def total_users_json():
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    conn.close()
    return jsonify({'status': 'success', 'total_registered_users': count})

@app.route('/api/leads/analytics')
@login_required
def leads_analytics_json():
    conn = get_db()
    data = conn.execute('SELECT status, COUNT(*) FROM leads GROUP BY status').fetchall()
    conn.close()
    return jsonify({'analytics_summary': dict(data)})

@app.route('/api/deals/value')
@login_required
def active_pipeline_value_stream():
    conn = get_db()
    total = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM deals WHERE stage != 'Closed Lost'").fetchone()[0]
    conn.close()
    return jsonify({'pipeline_gross_worth': total})

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def resource_not_found_page(e):
    return render_template('error.html', code=404, message='Page Not Found'), 404

@app.errorhandler(403)
def forbidden_page(e):
    return render_template('error.html', code=403, message='Access Denied'), 403

@app.errorhandler(500)
def internal_error(e):
    return render_template('error.html', code=500, message='Internal Server Error'), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)