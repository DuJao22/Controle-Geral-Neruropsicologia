import os
import sqlitecloud
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    """Get SQLiteCloud database connection"""
    conn = sqlitecloud.connect("sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/sistema_pacientes.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k")
    # SQLiteCloud doesn't support row_factory the same way, but we can work with tuples
    
    # Check and add carteirinha column if it doesn't exist
    try:
        cursor = conn.execute("PRAGMA table_info(pacientes)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'carteirinha' not in columns:
            conn.execute('ALTER TABLE pacientes ADD COLUMN carteirinha TEXT')
            conn.commit()
            print("Coluna carteirinha adicionada com sucesso")
    except Exception as e:
        print(f"Erro ao verificar/adicionar coluna carteirinha: {e}")
    
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    
    # Create tables individually (SQLiteCloud doesn't support executescript)
    tables = [
        '''CREATE TABLE IF NOT EXISTS medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            crm TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )''',
        '''CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL,
            carteirinha TEXT,
            data_inicio DATE NOT NULL,
            data_limite DATE NOT NULL,
            status TEXT DEFAULT 'ativo',
            medico_id INTEGER NOT NULL,
            FOREIGN KEY (medico_id) REFERENCES medicos (id)
        )''',
        '''CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            data DATE NOT NULL,
            observacoes TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )''',
        '''CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            numero TEXT NOT NULL,
            valor DECIMAL(10,2) NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_cadastro DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )''',
        '''CREATE TABLE IF NOT EXISTS laudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            data_upload DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )'''
    ]
    
    for table_sql in tables:
        conn.execute(table_sql)
    
    # Create admin user if not exists
    cursor = conn.execute('SELECT * FROM medicos WHERE email = ?', ('admin@admin.com',))
    admin = cursor.fetchone()
    if not admin:
        senha_hash = generate_password_hash('admin123')
        conn.execute('''
            INSERT INTO medicos (nome, email, senha, crm) 
            VALUES (?, ?, ?, ?)
        ''', ('Administrador', 'admin@admin.com', senha_hash, 'ADMIN'))
        conn.commit()
    
    conn.close()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database - tables already exist in SQLiteCloud
# init_db()

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('medico_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.execute('SELECT * FROM medicos WHERE email = ? AND ativo = 1', (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):  # user[3] = senha
            session['user_id'] = user[0]    # user[0] = id
            session['user_name'] = user[1]  # user[1] = nome
            session['is_admin'] = user[4] == 'ADMIN'  # user[4] = crm
            
            if session['is_admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('medico_dashboard'))
        else:
            flash('Email ou senha inválidos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get statistics
    stats = {}
    cursor = conn.execute('SELECT COUNT(*) as count FROM medicos WHERE ativo = 1 AND crm != "ADMIN"')
    stats['total_medicos'] = cursor.fetchone()[0]
    
    cursor = conn.execute('SELECT COUNT(*) as count FROM pacientes WHERE status = "ativo"')
    stats['total_pacientes'] = cursor.fetchone()[0]
    
    cursor = conn.execute('SELECT COUNT(*) as count FROM sessoes')
    stats['total_sessoes'] = cursor.fetchone()[0]
    
    cursor = conn.execute('SELECT COUNT(*) as count FROM senhas')
    stats['total_senhas'] = cursor.fetchone()[0]
    
    # Total revenue
    cursor = conn.execute('SELECT SUM(valor) as total FROM senhas')
    revenue = cursor.fetchone()
    stats['total_faturamento'] = revenue[0] if revenue[0] else 0
    
    # Revenue by doctor
    faturamento_medicos = conn.execute('''
        SELECT m.nome, COALESCE(SUM(s.valor), 0) as total
        FROM medicos m
        LEFT JOIN pacientes p ON m.id = p.medico_id
        LEFT JOIN senhas s ON p.id = s.paciente_id
        WHERE m.crm != "ADMIN" AND m.ativo = 1
        GROUP BY m.id, m.nome
        ORDER BY total DESC
    ''').fetchall()
    
    # Password types distribution
    tipos_senhas = conn.execute('''
        SELECT tipo, COUNT(*) as count, SUM(valor) as total
        FROM senhas
        GROUP BY tipo
    ''').fetchall()
    
    # Recent sessions - convert tuples to named objects
    sessoes_raw = conn.execute('''
        SELECT s.data, s.numero, p.nome as paciente, m.nome as medico
        FROM sessoes s
        JOIN pacientes p ON s.paciente_id = p.id
        JOIN medicos m ON p.medico_id = m.id
        ORDER BY s.data DESC
        LIMIT 10
    ''').fetchall()
    
    # Convert tuples to objects with named attributes
    sessoes_recentes = []
    for row in sessoes_raw:
        sessao = type('Sessao', (), {})()
        sessao.data = row[0]
        sessao.numero = row[1]
        sessao.paciente = row[2]
        sessao.medico = row[3]
        sessoes_recentes.append(sessao)
    
    # Patients near deadline
    today = datetime.now().date()
    warning_date = today + timedelta(days=7)  # 7 days warning
    
    pacientes_alerta = conn.execute('''
        SELECT p.nome, p.data_limite, m.nome as medico,
               COUNT(s.id) as sessoes_realizadas
        FROM pacientes p
        JOIN medicos m ON p.medico_id = m.id
        LEFT JOIN sessoes s ON p.id = s.paciente_id
        WHERE p.data_limite <= ? AND p.status = "ativo"
        GROUP BY p.id
        ORDER BY p.data_limite ASC
    ''', (warning_date,)).fetchall()
    
    conn.close()
    
    return render_template('admin_dashboard.html', 
                         stats=stats,
                         faturamento_medicos=faturamento_medicos,
                         tipos_senhas=tipos_senhas,
                         sessoes_recentes=sessoes_recentes,
                         pacientes_alerta=pacientes_alerta)

@app.route('/medico/dashboard')
def medico_dashboard():
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get doctor's patients
    cursor = conn.execute('''
        SELECT p.id, p.nome, p.cpf, p.carteirinha, p.data_inicio, p.data_limite, p.medico_id, p.status,
               COUNT(s.id) as sessoes_realizadas,
               (SELECT COUNT(*) FROM senhas WHERE paciente_id = p.id) as senhas_cadastradas
        FROM pacientes p
        LEFT JOIN sessoes s ON p.id = s.paciente_id
        WHERE p.medico_id = ?
        GROUP BY p.id, p.nome, p.cpf, p.carteirinha, p.data_inicio, p.data_limite, p.medico_id, p.status
        ORDER BY p.data_inicio DESC
    ''', (session['user_id'],))
    pacientes_raw = cursor.fetchall()
    
    # Convert tuples to objects with named attributes
    pacientes = []
    for row in pacientes_raw:
        paciente = type('Paciente', (), {})()
        paciente.id = row[0]
        paciente.nome = row[1]
        paciente.cpf = row[2]
        paciente.carteirinha = row[3]
        paciente.data_inicio = row[4]
        paciente.data_limite = row[5]
        paciente.medico_id = row[6]
        paciente.status = row[7]
        paciente.sessoes_realizadas = row[8]
        paciente.senhas_cadastradas = row[9]
        pacientes.append(paciente)
    
    # Check for patients near deadline
    today = datetime.now().date()
    warning_date = today + timedelta(days=7)
    
    alertas = []
    for paciente in pacientes:
        data_limite = datetime.strptime(paciente.data_limite, '%Y-%m-%d').date()
        if data_limite <= warning_date and paciente.status == 'ativo':
            days_left = (data_limite - today).days
            alertas.append({
                'paciente': paciente.nome,
                'dias_restantes': days_left,
                'id': paciente.id
            })
    
    conn.close()
    
    return render_template('medico_dashboard.html', 
                         pacientes=pacientes,
                         alertas=alertas)

@app.route('/medico/configuracoes', methods=['GET', 'POST'])
def medico_configuracoes():
    """Doctor can edit their own password"""
    if 'user_id' not in session or session.get('is_admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        senha_atual = request.form['senha_atual']
        nova_senha = request.form['nova_senha']
        confirma_senha = request.form['confirma_senha']
        
        # Validate passwords match
        if nova_senha != confirma_senha:
            flash('As senhas não coincidem', 'error')
            return render_template('medico_configuracoes.html')
        
        # Validate current password
        conn = get_db_connection()
        cursor = conn.execute('SELECT senha FROM medicos WHERE id = ?', (session['user_id'],))
        medico = cursor.fetchone()
        
        if not medico or not check_password_hash(medico[0], senha_atual):
            flash('Senha atual incorreta', 'error')
            conn.close()
            return render_template('medico_configuracoes.html')
        
        # Update password
        nova_senha_hash = generate_password_hash(nova_senha)
        conn.execute('UPDATE medicos SET senha = ? WHERE id = ?', (nova_senha_hash, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Senha alterada com sucesso!', 'success')
        return redirect(url_for('medico_dashboard'))
    
    return render_template('medico_configuracoes.html')

@app.route('/admin/novo_medico', methods=['GET', 'POST'])
def novo_medico():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        crm = request.form['crm']
        senha = request.form['senha']
        
        conn = get_db_connection()
        
        # Check if email already exists
        cursor = conn.execute('SELECT * FROM medicos WHERE email = ?', (email,))
        existing = cursor.fetchone()
        if existing:
            flash('Email já está em uso', 'error')
        else:
            senha_hash = generate_password_hash(senha)
            conn.execute('''
                INSERT INTO medicos (nome, email, senha, crm)
                VALUES (?, ?, ?, ?)
            ''', (nome, email, senha_hash, crm))
            conn.commit()
            flash('Médico cadastrado com sucesso!', 'success')
        
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    return render_template('novo_medico.html')

@app.route('/admin/medicos')
def listar_medicos():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    medicos_raw = conn.execute('''
        SELECT m.id, m.nome, m.email, m.crm, m.ativo, COUNT(p.id) as total_pacientes
        FROM medicos m
        LEFT JOIN pacientes p ON m.id = p.medico_id
        WHERE m.crm != "ADMIN"
        GROUP BY m.id, m.nome, m.email, m.crm, m.ativo
        ORDER BY m.nome
    ''').fetchall()
    conn.close()
    
    # Convert tuples to objects with named attributes
    medicos = []
    for row in medicos_raw:
        medico = type('Medico', (), {})()
        medico.id = row[0]
        medico.nome = row[1]
        medico.email = row[2]
        medico.crm = row[3]
        medico.ativo = row[4]
        medico.total_pacientes = row[5]
        medicos.append(medico)
    
    return render_template('listar_medicos.html', medicos=medicos)

@app.route('/admin/reset_password/<int:medico_id>', methods=['POST'])
def reset_password(medico_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        # Generate a simple default password
        nova_senha = "123456"  # You can make this more sophisticated
        senha_hash = generate_password_hash(nova_senha)
        
        conn = get_db_connection()
        conn.execute('UPDATE medicos SET senha = ? WHERE id = ?', (senha_hash, medico_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Senha resetada com sucesso. Nova senha: {nova_senha}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao resetar senha: {str(e)}'})

@app.route('/admin/toggle_status/<int:medico_id>/<int:status>', methods=['POST'])
def toggle_status(medico_id, status):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Acesso negado'})
    
    try:
        conn = get_db_connection()
        conn.execute('UPDATE medicos SET ativo = ? WHERE id = ?', (status, medico_id))
        conn.commit()
        conn.close()
        
        status_text = "ativado" if status == 1 else "desativado"
        return jsonify({
            'success': True, 
            'message': f'Médico {status_text} com sucesso!'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao alterar status: {str(e)}'})

@app.route('/admin/laudos_pacientes')
def admin_laudos_pacientes():
    """Admin can see all patient information and reports"""
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get all patients with their information, including medical data and reports
    pacientes_raw = conn.execute('''
        SELECT p.id, p.nome, p.cpf, p.carteirinha, p.data_inicio, p.data_limite, 
               m.nome as medico_nome, p.status,
               COUNT(DISTINCT s.id) as total_sessoes,
               COUNT(DISTINCT sen.id) as total_senhas,
               COUNT(DISTINCT l.id) as total_laudos,
               COALESCE(SUM(sen.valor), 0) as valor_total_senhas
        FROM pacientes p
        LEFT JOIN medicos m ON p.medico_id = m.id
        LEFT JOIN sessoes s ON p.id = s.paciente_id
        LEFT JOIN senhas sen ON p.id = sen.paciente_id
        LEFT JOIN laudos l ON p.id = l.paciente_id
        GROUP BY p.id, p.nome, p.cpf, p.carteirinha, p.data_inicio, p.data_limite, m.nome, p.status
        ORDER BY p.data_inicio DESC
    ''').fetchall()
    
    # Convert to objects
    pacientes = []
    for row in pacientes_raw:
        paciente = type('Paciente', (), {})()
        paciente.id = row[0]
        paciente.nome = row[1]
        paciente.cpf = row[2]
        paciente.carteirinha = row[3]
        paciente.data_inicio = row[4]
        paciente.data_limite = row[5]
        paciente.medico_nome = row[6]
        paciente.status = row[7]
        paciente.total_sessoes = row[8]
        paciente.total_senhas = row[9]
        paciente.total_laudos = row[10]
        paciente.valor_total_senhas = row[11]
        pacientes.append(paciente)
    
    conn.close()
    return render_template('admin_laudos_pacientes.html', pacientes=pacientes)

@app.route('/admin/paciente_completo/<int:paciente_id>')
def admin_paciente_completo(paciente_id):
    """Admin can see complete patient information including all financial data"""
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get patient info
    cursor = conn.execute('''
        SELECT p.*, m.nome as medico_nome 
        FROM pacientes p 
        JOIN medicos m ON p.medico_id = m.id 
        WHERE p.id = ?
    ''', (paciente_id,))
    paciente_raw = cursor.fetchone()
    
    if not paciente_raw:
        flash('Paciente não encontrado', 'error')
        return redirect(url_for('admin_laudos_pacientes'))
    
    # Convert patient to object
    paciente = type('Paciente', (), {})()
    paciente.id = paciente_raw[0]
    paciente.nome = paciente_raw[1]
    paciente.cpf = paciente_raw[2]
    paciente.data_inicio = paciente_raw[3]
    paciente.data_limite = paciente_raw[4]
    paciente.medico_id = paciente_raw[5]
    paciente.status = paciente_raw[6]
    paciente.medico_nome = paciente_raw[7]
    
    # Get sessions
    sessoes_raw = conn.execute('''
        SELECT * FROM sessoes WHERE paciente_id = ? ORDER BY data DESC
    ''', (paciente_id,)).fetchall()
    
    sessoes = []
    for row in sessoes_raw:
        sessao = type('Sessao', (), {})()
        sessao.id = row[0]
        sessao.paciente_id = row[1]
        sessao.numero = row[2]
        sessao.data = row[3]
        sessao.observacoes = row[4]
        sessoes.append(sessao)
    
    # Get senhas (passwords) with VALUES - Admin sees everything
    senhas_raw = conn.execute('''
        SELECT * FROM senhas WHERE paciente_id = ? ORDER BY data_cadastro DESC
    ''', (paciente_id,)).fetchall()
    
    senhas = []
    for row in senhas_raw:
        senha = type('Senha', (), {})()
        senha.id = row[0]
        senha.paciente_id = row[1]
        senha.tipo = row[2]
        senha.numero = row[3]
        senha.valor = row[4]  # Admin can see values
        senha.data_cadastro = row[5]
        senhas.append(senha)
    
    # Get laudos
    laudos_raw = conn.execute('''
        SELECT * FROM laudos WHERE paciente_id = ? ORDER BY data_upload DESC
    ''', (paciente_id,)).fetchall()
    
    laudos = []
    for row in laudos_raw:
        laudo = type('Laudo', (), {})()
        laudo.id = row[0]
        laudo.paciente_id = row[1]
        laudo.nome_arquivo = row[2]
        laudo.data_upload = row[3]
        laudos.append(laudo)
    
    conn.close()
    
    # Calculate remaining days
    today = datetime.now().date()
    data_limite = datetime.strptime(paciente.data_limite, '%Y-%m-%d').date()
    dias_restantes = (data_limite - today).days
    
    return render_template('admin_paciente_completo.html',
                         paciente=paciente, sessoes=sessoes, 
                         senhas=senhas, laudos=laudos, 
                         dias_restantes=dias_restantes)

@app.route('/novo_paciente', methods=['GET', 'POST'])
def novo_paciente():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        carteirinha = request.form.get('carteirinha', '')  # Optional field
        data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date()
        data_limite = data_inicio + timedelta(days=60)
        
        # Only doctors can register patients
        if session.get('is_admin'):
            flash('Apenas médicos podem cadastrar pacientes', 'error')
            return redirect(url_for('admin_dashboard'))
        
        medico_id = session['user_id']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO pacientes (nome, cpf, carteirinha, data_inicio, data_limite, medico_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nome, cpf, carteirinha, data_inicio, data_limite, medico_id))
        conn.commit()
        conn.close()
        
        flash('Paciente cadastrado com sucesso!', 'success')
        return redirect(url_for('medico_dashboard'))
    
    return render_template('novo_paciente.html')

@app.route('/paciente/<int:paciente_id>')
def paciente_detalhes(paciente_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get patient details
    cursor = conn.execute('''
        SELECT p.id, p.nome, p.cpf, p.carteirinha, p.data_inicio, p.data_limite, p.medico_id, p.status, m.nome as medico_nome
        FROM pacientes p
        JOIN medicos m ON p.medico_id = m.id
        WHERE p.id = ?
    ''', (paciente_id,))
    paciente_raw = cursor.fetchone()
    
    if not paciente_raw:
        flash('Paciente não encontrado', 'error')
        return redirect(url_for('medico_dashboard'))
    
    # Convert paciente to object
    paciente = type('Paciente', (), {})()
    paciente.id = paciente_raw[0]
    paciente.nome = paciente_raw[1]
    paciente.cpf = paciente_raw[2]
    paciente.carteirinha = paciente_raw[3]
    paciente.data_inicio = paciente_raw[4]
    paciente.data_limite = paciente_raw[5]
    paciente.medico_id = paciente_raw[6]
    paciente.status = paciente_raw[7]
    paciente.medico_nome = paciente_raw[8]
    
    # Check permissions
    if not session.get('is_admin') and paciente.medico_id != session['user_id']:
        flash('Acesso negado', 'error')
        return redirect(url_for('medico_dashboard'))
    
    # Get sessions
    cursor = conn.execute('''
        SELECT * FROM sessoes
        WHERE paciente_id = ?
        ORDER BY numero
    ''', (paciente_id,))
    sessoes_raw = cursor.fetchall()
    
    # Convert sessions to objects
    sessoes = []
    for row in sessoes_raw:
        sessao = type('Sessao', (), {})()
        sessao.id = row[0]
        sessao.paciente_id = row[1]
        sessao.numero = row[2]
        sessao.data = row[3]
        sessao.observacoes = row[4]
        sessoes.append(sessao)
    
    # Get passwords - hide values from doctors (non-admin users)
    if session.get('is_admin'):
        # Admin can see everything including values
        cursor = conn.execute('''
            SELECT id, paciente_id, tipo, numero, valor, data_cadastro FROM senhas
            WHERE paciente_id = ?
            ORDER BY data_cadastro
        ''', (paciente_id,))
        senhas_raw = cursor.fetchall()
        
        senhas = []
        for row in senhas_raw:
            senha = type('Senha', (), {})()
            senha.id = row[0]
            senha.paciente_id = row[1]
            senha.tipo = row[2]
            senha.numero = row[3]
            senha.valor = row[4]  # Admin sees values
            senha.data_cadastro = row[5]
            senha.status = 'liberada'  # Default status for display
            senhas.append(senha)
    else:
        # Doctors cannot see values (confidential information)
        cursor = conn.execute('''
            SELECT id, paciente_id, tipo, numero, data_cadastro FROM senhas
            WHERE paciente_id = ?
            ORDER BY data_cadastro
        ''', (paciente_id,))
        senhas_raw = cursor.fetchall()
        
        senhas = []
        for row in senhas_raw:
            senha = type('Senha', (), {})()
            senha.id = row[0]
            senha.paciente_id = row[1]
            senha.tipo = row[2]
            senha.numero = row[3]
            senha.valor = "***"  # Hidden from doctors
            senha.data_cadastro = row[4]
            senha.status = 'liberada'  # Default status for display
            senhas.append(senha)
    
    # Get laudo
    cursor = conn.execute('''
        SELECT * FROM laudos
        WHERE paciente_id = ?
        ORDER BY data_upload DESC
        LIMIT 1
    ''', (paciente_id,))
    laudo_raw = cursor.fetchone()
    
    laudo = None
    if laudo_raw:
        laudo = type('Laudo', (), {})()
        laudo.id = laudo_raw[0]
        laudo.paciente_id = laudo_raw[1]
        laudo.nome_arquivo = laudo_raw[2]
        laudo.data_upload = laudo_raw[3]
    
    conn.close()
    
    # Calculate remaining days
    today = datetime.now().date()
    data_limite = datetime.strptime(paciente.data_limite, '%Y-%m-%d').date()
    dias_restantes = (data_limite - today).days
    
    return render_template('paciente_detalhes.html',
                         paciente=paciente,
                         sessoes=sessoes,
                         senhas=senhas,
                         laudo=laudo,
                         dias_restantes=dias_restantes)

@app.route('/adicionar_sessao', methods=['POST'])
def adicionar_sessao():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    paciente_id = request.form['paciente_id']
    data = request.form['data']
    observacoes = request.form.get('observacoes', '')
    
    conn = get_db_connection()
    
    # Check permissions
    cursor = conn.execute('SELECT medico_id FROM pacientes WHERE id = ?', (paciente_id,))
    paciente_check = cursor.fetchone()
    if not session.get('is_admin') and paciente_check[0] != session['user_id']:
        flash('Acesso negado', 'error')
        conn.close()
        return redirect(url_for('medico_dashboard'))
    
    # Get next session number
    cursor = conn.execute('''
        SELECT MAX(numero) as max_numero FROM sessoes WHERE paciente_id = ?
    ''', (paciente_id,))
    last_session = cursor.fetchone()
    
    next_numero = (last_session[0] or 0) + 1
    
    if next_numero > 8:
        flash('Limite de 8 sessões atingido', 'error')
    else:
        conn.execute('''
            INSERT INTO sessoes (paciente_id, numero, data, observacoes)
            VALUES (?, ?, ?, ?)
        ''', (paciente_id, next_numero, data, observacoes))
        conn.commit()
        flash('Sessão adicionada com sucesso!', 'success')
    
    conn.close()
    return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))

@app.route('/adicionar_senha', methods=['POST'])
def adicionar_senha():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    paciente_id = request.form['paciente_id']
    tipo = request.form['tipo']
    numero = request.form['numero']
    
    conn = get_db_connection()
    
    # Check permissions
    cursor = conn.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_id,))
    paciente = cursor.fetchone()
    if not session.get('is_admin') and paciente[6] != session['user_id']:  # paciente[6] = medico_id
        flash('Acesso negado', 'error')
        conn.close()
        return redirect(url_for('medico_dashboard'))
    
    # Check session limit for passwords
    cursor = conn.execute('''
        SELECT COUNT(*) as count FROM sessoes WHERE paciente_id = ?
    ''', (paciente_id,))
    sessoes_count = cursor.fetchone()[0]
    
    if sessoes_count > 4:
        flash('Senhas só podem ser cadastradas até a 4ª sessão', 'error')
        conn.close()
        return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))
    
    # Check if password type already exists
    existing = conn.execute('''
        SELECT * FROM senhas WHERE paciente_id = ? AND tipo = ?
    ''', (paciente_id, tipo)).fetchone()
    
    if existing:
        flash(f'Senha do tipo {tipo} já foi cadastrada para este paciente', 'error')
    else:
        # Set value based on type
        valor = 100.00 if tipo == 'consulta' else 800.00
        
        conn.execute('''
            INSERT INTO senhas (paciente_id, tipo, numero, valor)
            VALUES (?, ?, ?, ?)
        ''', (paciente_id, tipo, numero, valor))
        conn.commit()
        flash('Senha adicionada com sucesso!', 'success')
    
    conn.close()
    return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))

@app.route('/upload_laudo', methods=['POST'])
def upload_laudo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    paciente_id = request.form['paciente_id']
    
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))
    
    file = request.files['arquivo']
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado', 'error')
        return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))
    
    if not allowed_file(file.filename):
        flash('Apenas arquivos PDF são permitidos', 'error')
        return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))
    
    conn = get_db_connection()
    
    # Check permissions
    cursor = conn.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_id,))
    paciente = cursor.fetchone()
    if not session.get('is_admin') and paciente[6] != session['user_id']:  # paciente[6] = medico_id
        flash('Acesso negado', 'error')
        conn.close()
        return redirect(url_for('medico_dashboard'))
    
    # Check if patient has 8 sessions or is being finalized
    cursor = conn.execute('''
        SELECT COUNT(*) as count FROM sessoes WHERE paciente_id = ?
    ''', (paciente_id,))
    sessoes_count = cursor.fetchone()[0]
    
    finalizar = request.form.get('finalizar') == 'on'
    
    if sessoes_count < 8 and not finalizar:
        flash('Laudo só pode ser enviado após 8 sessões ou marcando "Finalizar paciente"', 'error')
        conn.close()
        return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))
    
    # Save file
    filename = secure_filename(f"laudo_{paciente_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Save to database
    conn.execute('''
        INSERT INTO laudos (paciente_id, caminho_arquivo)
        VALUES (?, ?)
    ''', (paciente_id, filename))
    
    # Mark patient as finalized if requested
    if finalizar:
        conn.execute('''
            UPDATE pacientes SET status = 'finalizado' WHERE id = ?
        ''', (paciente_id,))
    
    conn.commit()
    conn.close()
    
    flash('Laudo enviado com sucesso!', 'success')
    return redirect(url_for('paciente_detalhes', paciente_id=paciente_id))

@app.route('/download_laudo/<filename>')
def download_laudo(filename):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/dashboard_data')
def dashboard_data():
    if not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db_connection()
    
    # Revenue by doctor for chart
    faturamento_data = conn.execute('''
        SELECT m.nome, COALESCE(SUM(s.valor), 0) as total
        FROM medicos m
        LEFT JOIN pacientes p ON m.id = p.medico_id
        LEFT JOIN senhas s ON p.id = s.paciente_id
        WHERE m.crm != "ADMIN" AND m.ativo = 1
        GROUP BY m.id, m.nome
        ORDER BY total DESC
    ''').fetchall()
    
    # Password types for pie chart
    tipos_data = conn.execute('''
        SELECT tipo, COUNT(*) as count
        FROM senhas
        GROUP BY tipo
    ''').fetchall()
    
    # Sessions timeline
    timeline_data = conn.execute('''
        SELECT DATE(s.data) as data, COUNT(*) as count
        FROM sessoes s
        WHERE s.data >= date('now', '-30 days')
        GROUP BY DATE(s.data)
        ORDER BY data
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        'faturamento': [{'nome': row[0], 'total': row[1]} for row in faturamento_data],
        'tipos_senhas': [{'tipo': row[0], 'count': row[1]} for row in tipos_data],
        'timeline': [{'data': row[0], 'count': row[1]} for row in timeline_data]
    })

@app.route('/relatorio_medico')
def relatorio_medico():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('is_admin'):
        return redirect(url_for('relatorio_admin'))
    
    conn = get_db_connection()
    medico_id = session['user_id']
    
    # Estatísticas do médico
    stats = {}
    cursor = conn.execute(
        'SELECT COUNT(*) as count FROM pacientes WHERE medico_id = ? AND status = "ativo"', 
        (medico_id,)
    )
    stats['total_pacientes'] = cursor.fetchone()[0]
    
    cursor = conn.execute('''
        SELECT COUNT(*) as count FROM sessoes s
        JOIN pacientes p ON s.paciente_id = p.id
        WHERE p.medico_id = ?
    ''', (medico_id,))
    stats['total_sessoes'] = cursor.fetchone()[0]
    
    cursor = conn.execute('''
        SELECT COUNT(*) as count FROM senhas s
        JOIN pacientes p ON s.paciente_id = p.id
        WHERE p.medico_id = ?
    ''', (medico_id,))
    stats['total_senhas'] = cursor.fetchone()[0]
    
    cursor = conn.execute('''
        SELECT COALESCE(SUM(s.valor), 0) as total FROM senhas s
        JOIN pacientes p ON s.paciente_id = p.id
        WHERE p.medico_id = ?
    ''', (medico_id,))
    revenue = cursor.fetchone()
    stats['total_faturamento'] = revenue[0] if revenue[0] else 0
    
    # Pacientes com progresso
    cursor = conn.execute('''
        SELECT p.id, p.nome, p.cpf, p.data_inicio, p.data_limite, p.status,
               COUNT(s.id) as sessoes_realizadas,
               (SELECT COUNT(*) FROM senhas WHERE paciente_id = p.id) as senhas_count,
               CASE 
                   WHEN julianday(p.data_limite) - julianday('now') < 0 THEN 'atrasado'
                   WHEN julianday(p.data_limite) - julianday('now') <= 7 THEN 'urgente'
                   ELSE 'normal'
               END as urgencia
        FROM pacientes p
        LEFT JOIN sessoes s ON p.id = s.paciente_id
        WHERE p.medico_id = ?
        GROUP BY p.id
        ORDER BY p.data_inicio DESC
    ''', (medico_id,))
    pacientes_raw = cursor.fetchall()
    
    # Convert tuples to objects with named attributes
    pacientes_progresso = []
    for row in pacientes_raw:
        paciente = type('Paciente', (), {})()
        paciente.id = row[0]
        paciente.nome = row[1]
        paciente.cpf = row[2]
        paciente.data_inicio = row[3]
        paciente.data_limite = row[4]
        paciente.status = row[5]
        paciente.sessoes_realizadas = row[6]
        paciente.senhas_count = row[7]
        paciente.urgencia = row[8]
        pacientes_progresso.append(paciente)
    
    # Sessões por mês (últimos 6 meses)
    cursor = conn.execute('''
        SELECT strftime('%Y-%m', s.data) as mes, COUNT(*) as total
        FROM sessoes s
        JOIN pacientes p ON s.paciente_id = p.id
        WHERE p.medico_id = ? AND s.data >= date('now', '-6 months')
        GROUP BY strftime('%Y-%m', s.data)
        ORDER BY mes
    ''', (medico_id,))
    sessoes_por_mes_raw = cursor.fetchall()
    
    # Convert to dict for JSON serialization
    sessoes_por_mes = [{'mes': row[0], 'total': row[1]} for row in sessoes_por_mes_raw]
    
    # Tipos de senhas do médico
    cursor = conn.execute('''
        SELECT s.tipo, COUNT(*) as count, SUM(s.valor) as total
        FROM senhas s
        JOIN pacientes p ON s.paciente_id = p.id
        WHERE p.medico_id = ?
        GROUP BY s.tipo
    ''', (medico_id,))
    tipos_senhas_raw = cursor.fetchall()
    
    # Convert to dict for JSON serialization
    tipos_senhas = [{'tipo': row[0], 'count': row[1], 'total': row[2]} for row in tipos_senhas_raw]
    
    conn.close()
    
    return render_template('relatorio_medico.html',
                         stats=stats,
                         pacientes=pacientes_progresso,
                         sessoes_por_mes=sessoes_por_mes,
                         tipos_senhas=tipos_senhas)

@app.route('/relatorio_admin')
def relatorio_admin():
    if not session.get('is_admin'):
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Estatísticas gerais
    stats = {}
    cursor = conn.execute(
        'SELECT COUNT(*) as count FROM medicos WHERE ativo = 1 AND crm != "ADMIN"'
    )
    stats['total_medicos'] = cursor.fetchone()[0]
    
    cursor = conn.execute(
        'SELECT COUNT(*) as count FROM pacientes WHERE status = "ativo"'
    )
    stats['total_pacientes'] = cursor.fetchone()[0]
    
    cursor = conn.execute(
        'SELECT COUNT(*) as count FROM sessoes'
    )
    stats['total_sessoes'] = cursor.fetchone()[0]
    
    cursor = conn.execute('SELECT SUM(valor) as total FROM senhas')
    revenue = cursor.fetchone()
    stats['total_faturamento'] = revenue[0] if revenue[0] else 0
    
    # Relatório por médico
    cursor = conn.execute('''
        SELECT m.nome, m.crm,
               COUNT(DISTINCT p.id) as pacientes_total,
               COUNT(DISTINCT CASE WHEN p.status = 'ativo' THEN p.id END) as pacientes_ativos,
               COUNT(s.id) as sessoes_total,
               COALESCE(SUM(se.valor), 0) as faturamento_total
        FROM medicos m
        LEFT JOIN pacientes p ON m.id = p.medico_id
        LEFT JOIN sessoes s ON p.id = s.paciente_id
        LEFT JOIN senhas se ON p.id = se.paciente_id
        WHERE m.crm != "ADMIN" AND m.ativo = 1
        GROUP BY m.id, m.nome, m.crm
        ORDER BY faturamento_total DESC
    ''')
    relatorio_medicos = cursor.fetchall()
    
    # Pacientes por status
    cursor = conn.execute('''
        SELECT status, COUNT(*) as count
        FROM pacientes
        GROUP BY status
    ''')
    pacientes_status = cursor.fetchall()
    
    # Evolução mensal
    cursor = conn.execute('''
        SELECT strftime('%Y-%m', s.data) as mes,
               COUNT(DISTINCT s.id) as sessoes,
               COUNT(DISTINCT p.id) as pacientes_unicos,
               COALESCE(SUM(se.valor), 0) as faturamento
        FROM sessoes s
        JOIN pacientes p ON s.paciente_id = p.id
        LEFT JOIN senhas se ON p.id = se.paciente_id
        WHERE s.data >= date('now', '-12 months')
        GROUP BY strftime('%Y-%m', s.data)
        ORDER BY mes
    ''')
    evolucao_mensal_raw = cursor.fetchall()
    
    # Convert to dict for JSON serialization
    evolucao_mensal = [{
        'mes': row[0], 
        'sessoes': row[1], 
        'pacientes_unicos': row[2],
        'faturamento': float(row[3])
    } for row in evolucao_mensal_raw]
    
    conn.close()
    
    return render_template('relatorio_admin.html',
                         stats=stats,
                         medicos=relatorio_medicos,
                         pacientes_status=pacientes_status,
                         evolucao_mensal=evolucao_mensal)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)