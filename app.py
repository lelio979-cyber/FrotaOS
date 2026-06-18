import streamlit as pd
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão de Frotas Pro", layout="wide", page_icon="🚚")

# --- BANCO DE DADOS (INICIALIZAÇÃO) ---
def init_db():
    conn = sqlite3.connect('frota_pro.db')
    c = conn.cursor()
    # Veículos
    c.execute('''CREATE TABLE IF NOT EXISTS veiculos 
                 (id INTEGER PRIMARY KEY, placa TEXT UNIQUE, modelo TEXT, marca TEXT, ano INTEGER, km_atual REAL, status TEXT)''')
    # Motoristas
    c.execute('''CREATE TABLE IF NOT EXISTS motoristas 
                 (id INTEGER PRIMARY KEY, nome TEXT, cnh TEXT, status TEXT)''')
    # Abastecimentos
    c.execute('''CREATE TABLE IF NOT EXISTS abastecimentos 
                 (id INTEGER PRIMARY KEY, placa TEXT, data TEXT, litro REAL, valor_total REAL, km_registro REAL, cartao TEXT)''')
    # Manutenções / OS
    c.execute('''CREATE TABLE IF NOT EXISTS ordens_servico 
                 (id INTEGER PRIMARY KEY, placa TEXT, descricao TEXT, custo REAL, data_entrada TEXT, status TEXT)''')
    # Checklists
    c.execute('''CREATE TABLE IF NOT EXISTS checklists 
                 (id INTEGER PRIMARY KEY, placa TEXT, data TEXT, motorista TEXT, itens_conformes TEXT, observacao TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE BANCO ---
def query_db(query, params=(), is_select=True):
    conn = sqlite3.connect('frota_pro.db')
    if is_select:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    else:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        conn.close()

# --- SIDEBAR NAV ---
st.sidebar.title("🚚 Frota Elite v1.0")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegação", [
    "📊 Dashboard Executivo", 
    "🚗 Cadastro de Veículos", 
    "👥 Motoristas",
    "⛽ Importar TicketLog", 
    "🔧 Ordens de Serviço", 
    "📋 Checklist Diário"
])

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard Executivo":
    st.title("📊 Dashboard Analítico da Frota")
    st.markdown("Visão em tempo real dos ~150 veículos leves.")
    
    # Métricas Principais
    df_v = query_db("SELECT * FROM veiculos")
    df_os = query_db("SELECT * FROM ordens_servico WHERE status = 'Aberta'")
    df_ab = query_db("SELECT * FROM abastecimentos")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Veículos", len(df_v))
    col2.metric("Veículos em Manutenção", len(df_os))
    col3.metric("Investimento Combustível (Mês)", f"R$ {df_ab['valor_total'].sum():,.2f}")
    col4.metric("KM Total Rodada", f"{df_v['km_atual'].sum():,.0f} km" if not df_v.empty else "0 km")
    
    st.markdown("---")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Status da Frota")
        if not df_v.empty:
            status_counts = df_v['status'].value_counts()
            st.bar_chart(status_counts)
        else:
            st.info("Nenhum veículo cadastrado.")
            
    with col_g2:
        st.subheader("Evolução de Custos com Abastecimento")
        if not df_ab.empty:
            df_ab['data'] = pd.to_datetime(df_ab['data'])
            df_gastos = df_ab.groupby(df_ab['data'].dt.strftime('%Y-%m'))['valor_total'].sum()
            st.line_chart(df_gastos)
        else:
            st.info("Sem dados de abastecimento disponíveis.")

# --- 2. CADASTRO DE VEÍCULOS ---
elif menu == "🚗 Cadastro de Veículos":
    st.title("🚗 Gestão e Cadastro de Veículos")
    
    with st.form("form_veiculo", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        placa = col1.text_input("Placa (AAA-0000)").upper()
        modelo = col2.text_input("Modelo")
        marca = col3.text_input("Marca")
        
        col4, col5, col6 = st.columns(3)
        ano = col4.number_input("Ano", min_value=2000, max_value=2027, value=2024)
        km = col5.number_input("KM Atual", min_value=0.0, step=100.0)
        status = col6.selectbox("Status Inicial", ["Ativo", "Em Manutenção", "Inativo"])
        
        submit = st.form_submit_button("Salvar Veículo")
        
    if submit:
        if placa and modelo:
            try:
                query_db("INSERT INTO veiculos (placa, modelo, marca, ano, km_atual, status) VALUES (?, ?, ?, ?, ?, ?)",
                         (placa, modelo, marca, ano, km, status), is_select=False)
                st.success(f"Veículo {placa} cadastrado com sucesso!")
            except:
                st.error("Erro: Esta placa já está cadastrada.")
        else:
            st.warning("Preencha os campos obrigatórios (Placa e Modelo).")
            
    st.markdown("### Veículos Cadastrados")
    df_veiculos = query_db("SELECT * FROM veiculos")
    st.dataframe(df_veiculos, use_container_width=True)

# --- 3. MOTORISTAS ---
elif menu == "👥 Motoristas":
    st.title("👥 Cadastro de Motoristas")
    
    with st.form("form_motorista", clear_on_submit=True):
        nome = st.text_input("Nome Completo")
        cnh = st.text_input("Número da CNH")
        status = st.selectbox("Status", ["Disponível", "Em Rota", "Afastado"])
        submit = st.form_submit_button("Cadastrar Motorista")
        
    if submit:
        if nome and cnh:
            query_db("INSERT INTO motoristas (nome, cnh, status) VALUES (?, ?, ?)", (nome, cnh, status), is_select=False)
            st.success(f"Motorista {nome} cadastrado com sucesso!")
            
    df_mot = query_db("SELECT * FROM motoristas")
    st.dataframe(df_mot, use_container_width=True)

# --- 4. IMPORTAR TICKETLOG (VERSÃO PDF ADAPTADA) ---
elif menu == "⛽ Importar TicketLog":
    st.title("⛽ Integração e Importação TicketLog (PDF)")
    st.markdown("Análise inteligente baseada no padrão visual do relatório Ticket Log.")
    
    import pdfplumber
    import re

    uploaded_file = st.file_uploader("Escolha o arquivo PDF original da TicketLog", type=['pdf'])
    
    if uploaded_file is not None:
        try:
            dados_extraidos = []
            
            with pdfplumber.open(uploaded_file) as pdf:
                for num_pag, pagina in enumerate(pdf.pages, 1):
                    texto = pagina.extract_text()
                    if not texto:
                        continue
                    
                    linhas = texto.split('\n')
                    for linha in linhas:
                        # Padrão: Começa com Data (DD/MM/AAAA HH:MM) seguido pelo número do cartão (6035...)
                        # Isso garante que estamos lendo apenas as linhas de transações reais
                        if re.search(r'^\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}\s+6035', linha):
                            partes = linha.split()
                            
                            try:
                                # Com base no padrão do relatório:
                                data_transacao = partes[0]  # DD/MM/AAAA
                                # partes[1] seria a hora (HH:MM)
                                # partes[2] seria o número do cartão (6035...)
                                
                                # A placa normalmente é o 4º elemento (índice 3)
                                placa = partes[3].upper().replace('-', '')
                                
                                # Os valores financeiros e numéricos ficam sempre no final da linha
                                valor_total_bruto = partes[-1]  # Último item
                                valor_litro_bruto = partes[-2]  # Penúltimo item
                                litros_bruto = partes[-3]       # Antepenúltimo item
                                km_bruto = partes[-5]           # KM fica antes do tipo de combustível
                                
                                # --- FUNÇÃO INTERNA PARA LIMPEZA DE TEXTO PARA FLOAT ---
                                def limpar_num(texto_num):
                                    # Remove R$, pontos de milhar e troca vírgula por ponto
                                    txt = texto_num.replace('R$', '').replace('.', '').replace(',', '.').strip()
                                    return float(txt)

                                km = limpar_num(km_bruto)
                                litros = limpar_num(litros_bruto)
                                valor_total = limpar_num(valor_total_bruto)
                                
                                # Regra de segurança: Se o KM vier negativo por erro de digitação da TicketLog, 
                                # convertemos para positivo para não quebrar o banco de dados
                                if km < 0:
                                    km = abs(km)

                                dados_extraidos.append({
                                    "Placa": placa,
                                    "Data": data_transacao,
                                    "Litros": litros,
                                    "Valor Total": valor_total,
                                    "Km": km
                                })
                            except Exception as erro_linha:
                                # Se alguma linha falhar no recorte, continua para a próxima sem travar
                                continue
            
            if dados_extraidos:
                df_ticket = pd.DataFrame(dados_extraidos)
                st.write(f"### Mapeamento Concluído: {len(df_ticket)} transações encontradas")
                st.dataframe(df_ticket, use_container_width=True)
                
                if st.button("Salvar Abastecimentos e Atualizar KMs da Frota"):
                    for _, row in df_ticket.iterrows():
                        # Insere o registro financeiro e de consumo
                        query_db('''INSERT INTO abastecimentos (placa, data, litro, valor_total, km_registro, cartao) 
                                    VALUES (?, ?, ?, ?, ?, ?)''', 
                                 (str(row['Placa']), str(row['Data']), float(row['Litros']), float(row['Valor Total']), float(row['Km']), "TicketLog PDF"), 
                                 is_select=False)
                        
                        # Atualiza o odômetro do veículo caso o KM do PDF seja mais recente/maior
                        query_db("UPDATE veiculos SET km_atual = ? WHERE placa = ? AND km_atual < ?", 
                                 (float(row['Km']), str(row['Placa']), float(row['Km'])), is_select=False)
                        
                    st.success("Tudo pronto! Relatório processado e armazenado com sucesso.")
            else:
                st.error("Não encontramos transações no formato padrão. Certifique-se de que o PDF não é uma imagem digitalizada escaneada.")
                
        except Exception as e:
            st.error(f"Falha crítica no processador de arquivos: {e}")
            
# --- 5. ORDENS DE SERVIÇO ---
elif menu == "🔧 Ordens de Serviço":
    st.title("🔧 Manutenção & Ordens de Serviço (O.S.)")
    
    df_v = query_db("SELECT placa FROM veiculos WHERE status='Ativo' or status='Em Manutenção'")
    
    with st.form("form_os", clear_on_submit=True):
        placa_os = st.selectbox("Selecione o Veículo", df_v['placa'].tolist() if not df_v.empty else ["Nenhum cadastrado"])
        descricao = st.text_area("Descrição do Serviço / Sinistro / Multa")
        custo = st.number_input("Custo Total (R$)", min_value=0.0, step=50.0)
        status_os = st.selectbox("Status da OS", ["Aberta", "Aprovada", "Concluída", "Recusada"])
        
        submit = st.form_submit_button("Gerar Ordem de Serviço")
        
    if submit and placa_os != "Nenhum cadastrado":
        data_atual = datetime.now().strftime("%Y-%m-%d")
        query_db("INSERT INTO ordens_servico (placa, descricao, custo, data_entrada, status) VALUES (?, ?, ?, ?, ?)",
                 (placa_os, descricao, custo, data_atual, status_os), is_select=False)
        
        if status_os == "Aberta":
            query_db("UPDATE veiculos SET status = 'Em Manutenção' WHERE placa = ?", (placa_os,), is_select=False)
        st.success("O.S. registrada com sucesso!")

    st.markdown("### Registro Geral de Manutenções e Custos Financeiros")
    df_todas_os = query_db("SELECT * FROM ordens_servico")
    st.dataframe(df_todas_os, use_container_width=True)

# --- 6. CHECKLIST DIÁRIO ---
elif menu == "📋 Checklist Diário":
    st.title("📋 Checklist de Liberação de Veículo")
    
    df_v = query_db("SELECT placa FROM veiculos WHERE status='Ativo'")
    df_m = query_db("SELECT nome FROM motoristas WHERE status='Disponível'")
    
    with st.form("form_checklist"):
        placa_ch = st.selectbox("Veículo", df_v['placa'].tolist() if not df_v.empty else ["Nenhum"])
        mot_ch = st.selectbox("Motorista", df_m['nome'].tolist() if not df_m.empty else ["Nenhum"])
        
        st.markdown("**Verificação de Itens Básicos:**")
        item1 = st.checkbox("Óleo do motor e fluídos em nível adequado?")
        item2 = st.checkbox("Pneus em bom estado e calibrados?")
        item3 = st.checkbox("Luzes, setas e faróis funcionando?")
        item4 = st.checkbox("Documentação do veículo em dia (CRLV)?")
        item5 = st.checkbox("Limpeza interna e externa em ordem?")
        
        obs = st.text_input("Observações adicionais")
        submit = st.form_submit_button("Salvar Checklist")
        
    if submit and placa_ch != "Nenhum":
        itens_ok = f"Oleo:{item1}, Pneus:{item2}, Luzes:{item3}, Doc:{item4}, Limpeza:{item5}"
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
        query_db("INSERT INTO checklists (placa, data, motorista, itens_conformes, observacao) VALUES (?, ?, ?, ?, ?)",
                 (placa_ch, data_atual, mot_ch, itens_ok, obs), is_select=False)
        st.success("Checklist salvo com sucesso! Veículo liberado para rodagem.")
