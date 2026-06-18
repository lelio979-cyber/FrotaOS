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

# --- 4. IMPORTAR TICKETLOG (VERSÃO COORDENADAS ESPACIAIS) ---
elif menu == "⛽ Importar TicketLog":
    st.title("⛽ Integração e Importação TicketLog (PDF)")
    st.markdown("Processador de alta fidelidade baseado no mapeamento geométrico de palavras.")
    
    import pdfplumber
    import re

    uploaded_file = st.file_uploader("Escolha o arquivo PDF original da TicketLog", type=['pdf'])
    
    if uploaded_file is not None:
        try:
            dados_extraidos = []
            
            with pdfplumber.open(uploaded_file) as pdf:
                for num_pag, pagina in enumerate(pdf.pages, 1):
                    # Extrai os objetos de palavras contendo o texto e suas coordenadas na página
                    palavras = pagina.extract_words(x_tolerance=3, y_tolerance=3)
                    
                    if not palavras:
                        continue
                    
                    # Agrupa as palavras por linha (baseado na posição vertical 'top')
                    linhas_dict = {}
                    for p in palavras:
                        # Arredonda a posição vertical para agrupar palavras na mesma linha física
                        y_pos = round(p['top'], 1)
                        
                        encontrou_linha = False
                        for k in linhas_dict.keys():
                            if abs(k - y_pos) < 3: # Margem de tolerância vertical
                                linhas_dict[k].append(p)
                                encontrou_linha = True
                                break
                        if not encontrou_linha:
                            linhas_dict[y_pos] = [p]
                    
                    # Processa cada linha ordenada de cima para baixo
                    for y in sorted(linhas_dict.keys()):
                        # Ordena as palavras da linha da esquerda para a direita
                        palavras_linha = sorted(linhas_dict[y], key=lambda x: x['x0'])
                        
                        # Transforma em texto corrido com espaços forçados para análise de estrutura básica
                        texto_linha = " ".join([p['text'] for p in palavras_linha])
                        
                        # 1. Filtro: A linha precisa começar com data
                        if not re.match(r'^\d{2}/\d{2}/\d{4}', texto_linha):
                            continue
                        
                        # 2. Localiza a Placa Mercosul ou Antiga
                        busca_placa = re.search(r'([A-Z]{3}[0-9][A-Z0-9][0-9]{2})', texto_linha, re.IGNORECASE)
                        if not busca_placa:
                            continue
                        placa = busca_placa.group(1).upper()
                        
                        try:
                            # 3. EXTRAÇÃO CIRÚRGICA DE VALORES PELA EXTREMIDADE DIREITA (COORDENADAS X)
                            # Filtramos apenas blocos que possuem números ou vírgulas
                            blocos_numericos = []
                            for p in palavras_linha:
                                txt = p['text'].replace('R$', '').strip()
                                # Se contém número ou caracteres matemáticos válidos
                                if re.search(r'[\d\.,-]', txt):
                                    blocos_numericos.append(p)
                            
                            if len(blocos_numericos) < 3:
                                continue
                                
                            # Ordena estritamente pela posição horizontal final (x1)
                            blocos_numericos = sorted(blocos_numericos, key=lambda x: x['x1'])
                            
                            # O valor total e os litros ficam sempre nas últimas colunas (maiores coordenadas X)
                            txt_total = blocos_numericos[-1]['text']
                            txt_litros = blocos_numericos[-3]['text'] if len(blocos_numericos) >= 3 else blocos_numericos[-2]['text']
                            
                            # Para o KM, buscamos o primeiro bloco numérico longo (geralmente com ponto) 
                            # que aparece após a posição da placa
                            txt_km = "0"
                            for b in blocos_numericos:
                                # Se o bloco está à direita da placa e se assemelha a um odômetro
                                if b['x0'] > palavras_linha[[p['text'] for p in palavras_linha].index(busca_placa.group(0))]['x1']:
                                    teste_km = b['text'].replace('.', '').replace('-', '').strip()
                                    if teste_km.isdigit() and len(teste_km) >= 3 and b != blocos_numericos[-1] and b != blocos_numericos[-3]:
                                        txt_km = b['text']
                                        break
                            
                            # Tratamento e conversão limpa de strings aglutinadas remanescentes
                            def limpar_e_converter(texto_val):
                                # Se houver caracteres grudados extras no bloco, extrai apenas o primeiro padrão decimal
                                match = re.search(r'(-?[\d\.,]+)', texto_val)
                                if match:
                                    v = match.group(1)
                                    return float(v.replace('.', '').replace(',', '.'))
                                return 0.0
                                
                            valor_total = limpar_e_converter(txt_total)
                            litros = limpar_e_converter(txt_litros)
                            km = abs(limpar_e_converter(txt_km))
                            
                            data_transacao = texto_linha[:10]
                            
                            dados_extraidos.append({
                                "Placa": placa,
                                "Data": data_transacao,
                                "Litros": litros,
                                "Valor Total": valor_total,
                                "Km": km
                            })
                        except:
                            continue

            if dados_extraidos:
                df_ticket = pd.DataFrame(dados_extraidos)
                st.success(f"🎉 Sucesso definitivo! {len(df_ticket)} registros extraídos por mapeamento geométrico.")
                st.dataframe(df_ticket, use_container_width=True)
                
                if st.button("Confirmar e Salvar no Banco"):
                    for _, row in df_ticket.iterrows():
                        query_db('''INSERT INTO abastecimentos (placa, data, litro, valor_total, km_registro, cartao) 
                                    VALUES (?, ?, ?, ?, ?, ?)''', 
                                 (str(row['Placa']), str(row['Data']), float(row['Litros']), float(row['Valor Total']), float(row['Km']), "TicketLog PDF"), 
                                 is_select=False)
                        
                        query_db("UPDATE veiculos SET km_atual = ? WHERE placa = ? AND km_atual < ?", 
                                 (float(row['Km']), str(row['Placa']), float(row['Km'])), is_select=False)
                    st.success("Tudo atualizado com sucesso no banco de dados!")
            else:
                st.error("Não foi possível decodificar as colunas mesmo usando mapeamento espacial. O arquivo está corrompido?")
                
        except Exception as e:
            st.error(f"Erro no motor de processamento geométrico: {e}")
            
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
