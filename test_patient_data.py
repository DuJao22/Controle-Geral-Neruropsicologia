#!/usr/bin/env python3
"""
Script para criar dados de teste para o sistema de pacientes
"""

import sqlitecloud
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

def get_db_connection():
    """Get SQLiteCloud database connection"""
    conn = sqlitecloud.connect(
        "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/sistema_pacientes.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"
    )
    return conn

def create_test_data():
    """
    Cria dados de teste: 1 médico e 2 pacientes com laudos
    """
    print("Criando dados de teste...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Criar um médico de teste
        senha_hash = generate_password_hash('123456')
        cursor.execute(
            'INSERT INTO medicos (nome, email, senha, crm, ativo) VALUES (?, ?, ?, ?, ?)',
            ('Dr. João Silva', 'joao@teste.com', senha_hash, 'CRM-12345', 1)
        )
        medico_id = cursor.lastrowid
        print(f"✓ Médico criado: Dr. João Silva (ID: {medico_id})")
        
        # 2. Criar pacientes de teste
        hoje = datetime.now().date()
        data_limite = hoje + timedelta(days=30)
        
        pacientes = [
            ('Maria Santos', '12345678901', hoje, data_limite),
            ('José Silva', '98765432100', hoje, data_limite)
        ]
        
        paciente_ids = []
        for nome, cpf, data_inicio, data_limite in pacientes:
            cursor.execute(
                'INSERT INTO pacientes (nome, cpf, data_inicio, data_limite, medico_id) VALUES (?, ?, ?, ?, ?)',
                (nome, cpf, data_inicio, data_limite, medico_id)
            )
            paciente_id = cursor.lastrowid
            paciente_ids.append(paciente_id)
            print(f"✓ Paciente criado: {nome} - CPF: {cpf} (ID: {paciente_id})")
            
            # Criar algumas sessões
            cursor.execute(
                'INSERT INTO sessoes (paciente_id, numero, data, observacoes) VALUES (?, ?, ?, ?)',
                (paciente_id, 1, hoje, 'Primeira sessão - avaliação inicial')
            )
            cursor.execute(
                'INSERT INTO sessoes (paciente_id, numero, data, observacoes) VALUES (?, ?, ?, ?)',
                (paciente_id, 2, hoje + timedelta(days=7), 'Segunda sessão - continuidade do tratamento')
            )
            
            # Criar uma senha
            cursor.execute(
                'INSERT INTO senhas (paciente_id, tipo, numero, valor) VALUES (?, ?, ?, ?)',
                (paciente_id, 'consulta', f'CONS{paciente_id:03d}', 150.00)
            )
            
        # 3. Criar arquivo de teste para laudo
        import os
        upload_dir = 'uploads'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        # Criar arquivo de teste
        test_file = os.path.join(upload_dir, 'laudo_teste_maria.pdf')
        with open(test_file, 'w') as f:
            f.write('%PDF-1.4\n%Teste de laudo para Maria Santos\nEste é um arquivo de teste para demonstrar o download de laudos.')
        
        # Inserir laudo no banco
        cursor.execute(
            'INSERT INTO laudos (paciente_id, caminho_arquivo, data_upload) VALUES (?, ?, ?)',
            (paciente_ids[0], 'laudo_teste_maria.pdf', datetime.now())
        )
        
        print(f"✓ Laudo criado para Maria Santos")
        
        conn.commit()
        
        print("\n" + "="*50)
        print("DADOS DE TESTE CRIADOS COM SUCESSO!")
        print("="*50)
        print("\n📊 Dados criados:")
        print("✓ 1 médico: Dr. João Silva (joao@teste.com / 123456)")
        print("✓ 2 pacientes:")
        print("  - Maria Santos (CPF: 123.456.789-01) - Com laudo")
        print("  - José Silva (CPF: 987.654.321-00)")
        print("✓ 4 sessões (2 para cada paciente)")
        print("✓ 2 senhas de consulta")
        print("✓ 1 laudo de teste")
        print("\n🧪 Para testar a área do paciente:")
        print("- Acesse /paciente/login")
        print("- Use CPF: 12345678901 (Maria Santos - com laudo)")
        print("- Use CPF: 98765432100 (José Silva - sem laudo)")
        print("="*50)
        
    except Exception as e:
        print(f"ERRO: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_test_data()