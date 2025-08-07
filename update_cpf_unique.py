#!/usr/bin/env python3
"""
Script para atualizar a tabela pacientes e garantir que o CPF seja único
"""

import sqlitecloud

def get_db_connection():
    """Get SQLiteCloud database connection"""
    conn = sqlitecloud.connect(
        "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/sistema_pacientes.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"
    )
    return conn

def update_cpf_unique():
    """
    Atualiza a estrutura da tabela pacientes para garantir que CPF seja único
    """
    print("Atualizando estrutura da tabela pacientes...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Primeiro, verificar se já existe um índice único para CPF
        cursor.execute("PRAGMA index_list(pacientes)")
        indexes = cursor.fetchall()
        
        cpf_unique_exists = False
        for index in indexes:
            cursor.execute(f"PRAGMA index_info({index[1]})")
            index_info = cursor.fetchall()
            for info in index_info:
                if info[2] == 'cpf':
                    cpf_unique_exists = True
                    break
        
        if not cpf_unique_exists:
            # Criar índice único para CPF
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_pacientes_cpf_unique ON pacientes(cpf)")
            conn.commit()
            print("✓ Índice único criado para CPF com sucesso!")
        else:
            print("✓ CPF já tem restrição de unicidade")
            
        print("✓ Atualização concluída!")
        
    except Exception as e:
        print(f"Erro durante atualização: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_cpf_unique()