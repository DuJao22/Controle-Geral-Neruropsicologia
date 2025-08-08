#!/usr/bin/env python3
"""
Script para resetar os dados do sistema, mantendo apenas o usuário admin.
Apaga todos os pacientes, médicos (exceto admin), sessões, senhas e laudos.
"""

import os
import sqlitecloud
from werkzeug.security import generate_password_hash
import shutil

def get_db_connection():
    """Get SQLiteCloud database connection"""
    conn = sqlitecloud.connect(
        "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/sistema_pacientes.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"
    )
    return conn

def reset_system_data():
    """
    Reseta todos os dados do sistema, mantendo apenas o admin.
    """
    print("Iniciando reset do sistema...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Primeiro, apagar todos os laudos (para não ter problemas com foreign keys)
        print("Apagando todos os laudos...")
        cursor.execute("DELETE FROM laudos")
        
        # 2. Apagar todas as senhas
        print("Apagando todas as senhas...")
        cursor.execute("DELETE FROM senhas")
        
        # 3. Apagar todas as sessões
        print("Apagando todas as sessões...")
        cursor.execute("DELETE FROM sessoes")
        
        # 4. Apagar todos os pacientes
        print("Apagando todos os pacientes...")
        cursor.execute("DELETE FROM pacientes")
        
        # 5. Apagar todos os médicos, exceto o admin
        print("Apagando todos os médicos (exceto admin)...")
        cursor.execute("DELETE FROM medicos WHERE email != 'admin@gmail.com'")
        
        # 6. Garantir que o admin existe com as credenciais corretas
        print("Verificando/atualizando credenciais do admin...")
        cursor.execute('SELECT * FROM medicos WHERE email = ?', ('admin@gmail.com',))
        admin = cursor.fetchone()
        
        if not admin:
            # Se não existe, criar
            senha_hash = generate_password_hash('20e10')
            cursor.execute(
                'INSERT INTO medicos (nome, email, senha, crm, ativo) VALUES (?, ?, ?, ?, ?)',
                ('Administrador', 'admin@gmail.com', senha_hash, 'ADMIN', 1)
            )
            print("Admin criado com sucesso!")
        else:
            # Se existe, atualizar senha para garantir que está correta
            senha_hash = generate_password_hash('20e10')
            cursor.execute(
                'UPDATE medicos SET senha = ?, nome = ?, crm = ?, ativo = 1 WHERE email = ?',
                (senha_hash, 'Administrador', 'ADMIN', 'admin@gmail.com')
            )
            print("Credenciais do admin atualizadas!")
        
        # Commit das mudanças
        conn.commit()
        
        # 7. Limpar arquivos de upload (opcional)
        print("Limpando arquivos de upload...")
        upload_folder = 'uploads'
        if os.path.exists(upload_folder):
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Arquivo removido: {filename}")
                except Exception as e:
                    print(f"Erro ao remover arquivo {filename}: {e}")
        
        print("\n" + "="*50)
        print("RESET CONCLUÍDO COM SUCESSO!")
        print("="*50)
        print("Dados removidos:")
        print("✓ Todos os pacientes")
        print("✓ Todos os médicos (exceto admin)")
        print("✓ Todas as sessões")
        print("✓ Todas as senhas")
        print("✓ Todos os laudos")
        print("✓ Todos os arquivos de upload")
        print("\nLogin do admin mantido:")
        print("Email: admin@gmail.com")
        print("Senha: 20e10")
        print("="*50)
        
    except Exception as e:
        print(f"ERRO durante o reset: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    # Execução automática do reset
    print("ATENÇÃO: Este script irá apagar TODOS os dados do sistema!")
    print("Serão removidos:")
    print("- Todos os pacientes")
    print("- Todos os médicos (exceto admin)")
    print("- Todas as sessões")
    print("- Todas as senhas")
    print("- Todos os laudos")
    print("- Todos os arquivos de upload")
    print("\nApenas o login do admin será mantido (admin@gmail.com / 20e10)")
    print("\nIniciando reset automaticamente...")
    
    reset_system_data()