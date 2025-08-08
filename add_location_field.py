#!/usr/bin/env python3
"""
Script para adicionar campo de localização na tabela de pacientes
"""

import sqlitecloud

def get_db_connection():
    """Get SQLiteCloud database connection"""
    conn = sqlitecloud.connect(
        "sqlitecloud://cmq6frwshz.g4.sqlite.cloud:8860/sistema_pacientes.db?apikey=Dor8OwUECYmrbcS5vWfsdGpjCpdm9ecSDJtywgvRw8k"
    )
    return conn

def add_location_field():
    """
    Adiciona campo de localização na tabela pacientes
    """
    print("Adicionando campo de localização...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(pacientes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'localizacao' not in columns:
            cursor.execute('ALTER TABLE pacientes ADD COLUMN localizacao TEXT DEFAULT "Belo Horizonte"')
            conn.commit()
            print("✓ Coluna 'localizacao' adicionada com sucesso!")
        else:
            print("✓ Coluna 'localizacao' já existe")
            
        print("✓ Atualização concluída!")
        
    except Exception as e:
        print(f"Erro durante atualização: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_location_field()