#!/usr/bin/env python3
"""
Script para criar dados de teste com localização para verificar a nova funcionalidade
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

def create_location_test_data():
    """
    Cria pacientes de teste para diferentes localizações
    """
    print("Criando dados de teste com localização...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Buscar médicos existentes
        cursor.execute('SELECT id FROM medicos WHERE crm != "ADMIN" LIMIT 1')
        medico = cursor.fetchone()
        
        if not medico:
            # Criar um médico se não existir
            senha_hash = generate_password_hash('123456')
            cursor.execute(
                'INSERT INTO medicos (nome, email, senha, crm, ativo) VALUES (?, ?, ?, ?, ?)',
                ('Dr. Teste Localização', 'teste_local@teste.com', senha_hash, 'CRM-LOC123', 1)
            )
            medico_id = cursor.lastrowid
        else:
            medico_id = medico[0]
        
        # Criar pacientes para cada localização
        hoje = datetime.now().date()
        data_limite = hoje + timedelta(days=30)
        
        pacientes_localizacao = [
            ('Ana Silva BH', '11111111111', 'Belo Horizonte'),
            ('Carlos Santos Contagem', '22222222222', 'Contagem'), 
            ('Maria Oliveira Divinópolis', '33333333333', 'Divinópolis'),
        ]
        
        for nome, cpf, localizacao in pacientes_localizacao:
            # Verificar se já existe
            cursor.execute('SELECT id FROM pacientes WHERE cpf = ?', (cpf,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute(
                    'INSERT INTO pacientes (nome, cpf, localizacao, data_inicio, data_limite, medico_id) VALUES (?, ?, ?, ?, ?, ?)',
                    (nome, cpf, localizacao, hoje, data_limite, medico_id)
                )
                paciente_id = cursor.lastrowid
                print(f"✓ Paciente criado: {nome} - {localizacao} (CPF: {cpf})")
                
                # Criar arquivo de laudo teste
                import os
                upload_dir = 'uploads'
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                    
                test_file = os.path.join(upload_dir, f'laudo_teste_{localizacao.lower().replace(" ", "_")}.pdf')
                with open(test_file, 'w') as f:
                    f.write(f'%PDF-1.4\n%Laudo de teste para {nome}\nLocal de atendimento: {localizacao}')
                
                # Inserir laudo no banco
                cursor.execute(
                    'INSERT INTO laudos (paciente_id, caminho_arquivo, data_upload) VALUES (?, ?, ?)',
                    (paciente_id, f'laudo_teste_{localizacao.lower().replace(" ", "_")}.pdf', datetime.now())
                )
            else:
                print(f"✓ Paciente já existe: {nome} - {localizacao}")
        
        conn.commit()
        
        print("\n" + "="*50)
        print("DADOS DE TESTE COM LOCALIZAÇÃO CRIADOS!")
        print("="*50)
        print("\n📍 Teste os seguintes CPFs:")
        print("- 11111111111 (Ana Silva BH - Belo Horizonte)")
        print("- 22222222222 (Carlos Santos - Contagem)")
        print("- 33333333333 (Maria Oliveira - Divinópolis)")
        print("\n🏥 Acesse /paciente/login para testar")
        print("="*50)
        
    except Exception as e:
        print(f"ERRO: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_location_test_data()