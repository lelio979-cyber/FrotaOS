import sqlite3

def inicializar_banco():
    conn = sqlite3.connect('gestao_frotas.db')
    cursor = conn.cursor()
    
    # 1. Veículos e Trechos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            placa TEXT PRIMARY KEY,
            modelo TEXT,
            trecho_atual TEXT,              -- Trecho/Rota onde o veículo está operando
            km_atual INTEGER,
            status TEXT DEFAULT 'Disponível', -- Disponível, Em Manutenção, Reserva
            km_proxima_revisao INTEGER       -- Alerta de revisão (Ex: 10.000 em 10.000)
        )
    ''')
    
    # 2. Checklists (O Foco Principal do Operador)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            tipo_movimentacao TEXT, -- Entrada de Oficina, Saída de Oficina, Novo Contrato, Devolução, Substituição
            km INTEGER,
            combustivel TEXT,
            estado_pneus TEXT,
            avarias_sinistros TEXT,
            operador TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 3. Ordens de Serviço (OS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            tipo_manutencao TEXT, -- Preventiva ou Corretiva
            descricao TEXT,
            custo REAL,
            status TEXT DEFAULT 'Aguardando Aprovação' -- Aguardando Aprovação, Em Andamento, Encerrado
        )
    ''')

    # 4. Custos Financeiros Gerais (Combustível, Pedágio, Sinistros)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            tipo_custo TEXT, -- Abastecimento, Pedágio, Sinistro, Contrato
            valor REAL,
            data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 5. Multas Automáticas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS multas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            data TEXT,
            endereco TEXT,
            codigo_multa TEXT,
            gravidade TEXT,
            pontos INTEGER,
            valor REAL,
            descricao TEXT
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    inicializar_banco()
    print("Banco de dados configurado com sucesso!")
