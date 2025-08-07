import sqlite3
from werkzeug.security import generate_password_hash


def init_database():
    conn = sqlite3.connect('neuropsicologia.db')
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            crm TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL,
            data_inicio DATE NOT NULL,
            data_limite DATE NOT NULL,
            status TEXT DEFAULT 'ativo',
            medico_id INTEGER NOT NULL,
            FOREIGN KEY (medico_id) REFERENCES medicos (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            data DATE NOT NULL,
            observacoes TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            numero TEXT NOT NULL,
            valor DECIMAL(10,2) NOT NULL,
            status TEXT DEFAULT 'pendente',
            data_cadastro DATE DEFAULT CURRENT_DATE,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS laudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            caminho_arquivo TEXT NOT NULL,
            data_upload DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    ''')

    # Create admin user
    cursor.execute('SELECT * FROM medicos WHERE email = ?',
                   ('admin@admin.com', ))
    if not cursor.fetchone():
        admin_password = generate_password_hash('20e10')
        cursor.execute(
            '''
            INSERT INTO medicos (nome, email, senha, crm)
            VALUES (?, ?, ?, ?)
        ''', ('Administrador', 'admin@gmail.com', admin_password, 'ADMIN'))

    conn.commit()
    conn.close()
    print("Database initialized successfully!")


if __name__ == '__main__':
    init_database()
