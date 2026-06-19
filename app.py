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

# --- 4. IMPORTAR TICKETLOG (VERSÃO MÁXIMA ROBUSTEZ - FATIAMENTO REVERSO FIXO) ---
elif menu == "⛽ Importar TicketLog":
    st.title("⛽ Integração e Importação TicketLog (PDF)")
    st.markdown("Processador por desconstrução de strings contínuas via Regex e fatiamento reverso fixo.")
    
    import pdfplumber
    import re

    uploaded_file = st.file_uploader("Escolha o arquivo PDF original da TicketLog", type=['pdf'])
    
    if uploaded_file is not None:
        try:
            dados_extraidos = []
            texto_cru_debug = ""
            
            with pdfplumber.open(uploaded_file) as pdf:
                for num_pag, pagina in enumerate(pdf.pages, 1):
                    texto = pagina.extract_text()
                    if not texto:
                        continue
                    
                    texto_cru_debug += f"\n--- PÁGINA {num_pag} ---\n" + texto
                    
                    for linha in texto.split('\n'):
                        linha = linha.strip().replace('R$', '').replace(' ', '')
                        
                        # 1. Filtro inicial: Linha deve começar com data válida
                        if not re.match(r'^\d{2}/\d{2}/\d{4}', linha):
                            continue
                            
                        # 2. Localiza e isola a Placa do veículo
                        busca_placa = re.search(r'([A-Z]{3}[0-9][A-Z0-9][0-9]{2})', linha, re.IGNORECASE)
                        if not busca_placa:
                            continue
                        placa = busca_placa.group(1).upper()
                        
                        try:
                            # 3. EXTRAÇÃO CIRÚRGICA DE VALORES FINANCEIROS DE TRÁS PARA FRENTE
                            # Isola todo o bloco numérico final da linha grudada
                            match_final = re.search(r'(-?[\d\.,]+)$', linha)
                            if not match_final:
                                continue
                                
                            bloco_numerico = match_final.group(1) # Ex: -31.34444,115,89255,27
                            partes = bloco_numerico.split(',')
                            
                            if len(partes) >= 3:
                                # Captura do Valor Total (Última vírgula)
                                centavos_total = partes[-1]
                                # Pega apenas os dígitos numéricos colados antes da última vírgula
                                inteiro_total = re.findall(r'\d+', partes[-2])[-1]
                                valor_total = float(f"{inteiro_total}.{centavos_total}")
                                
                                # Captura dos Litros (Penúltima vírgula)
                                centavos_litros = partes[1][:2]
                                inteiro_litros = re.findall(r'\d+', partes[0])[-1]
                                litros = float(f"{inteiro_litros}.{centavos_litros}")
                                
                                # 4. EXTRAÇÃO DO KM POR LOCALIZAÇÃO DE PADRÃO (EIXO ESQUERDO)
                                # Em vez de cortar o bloco numérico final, buscamos o primeiro número
                                # com ponto (formato de milhar de KM) que aparece logo após a placa.
                                idx_fim_placa = linha.find(placa) + len(placa)
                                texto_pos_placa = linha[idx_fim_placa:]
                                
                                # Busca um número contendo ponto decimal (Ex: 31.344 ou -31.344)
                                busca_km = re.search(r'(-?\d+\.\d+)', texto_pos_placa)
                                if busca_km:
                                    km_txt = busca_km.group(1).replace('.', '').replace('-', '').strip()
                                    km = float(km_txt) if km_txt.isdigit() else 0.0
                                else:
                                    km = 0.0
                                
                                dados_extraidos.append({
                                    "Placa": placa,
                                    "Data": linha[:10],
                                    "Litros": litros,
                                    "Valor Total": valor_total,
                                    "Km": km
                                })
                        except:
                            continue

            if dados_extraidos:
                df_ticket = pd.DataFrame(dados_extraidos)
                st.success(f"🎉 Sucesso! Mapeamento concluído com {len(df_ticket)} registros processados.")
                st.dataframe(df_ticket, use_container_width=True)
                
                if st.button("Confirmar e Salvar no Banco"):
                    for _, row in df_ticket.iterrows():
                        query_db('''INSERT INTO abastecimentos (placa, data, litro, valor_total, km_registro, cartao) 
                                    VALUES (?, ?, ?, ?, ?, ?)''', 
                                 (str(row['Placa']), str(row['Data']), float(row['Litros']), float(row['Valor Total']), float(row['Km']), "TicketLog PDF"), 
                                 is_select=False)
                        
                        query_db("UPDATE veiculos SET km_atual = ? WHERE placa = ? AND km_atual < ?", 
                                 (float(row['Km']), str(row['Placa']), float(row['Km'])), is_select=False)
                    st.success("Dados gravados com sucesso!")
            else:
                st.error("Erro crítico na análise dos blocos de dados.")
                with st.expander("Visualizar texto cru capturado (Debug)"):
                    st.code(texto_cru_debug[:3000])
                    
        except Exception as e:
            st.error(f"Erro no motor de processamento: {e}")
            
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
