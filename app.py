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

def renderizar_checklist_frota(tipo_evento, chave_unica):
    """
    Renderiza o formulário padrão de checklist para qualquer movimentação de veículo.
    'tipo_evento' define o contexto (Ex: Entry, Exit, Novo Contrato)
    'chave_unica' evita conflitos de ID de componentes do Streamlit na mesma tela.
    """
    st.markdown(f"### 📋 Checklist de Inspeção OBRIGATÓRIA - {tipo_evento}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("**📱 Itens Externos**")
        pneus = st.checkbox("Pneus em bom estado (e estepe)", key=f"ch_pneus_{chave_unica}")
        avarias = st.checkbox("Sem avarias na lataria/riscos", key=f"ch_avarias_{chave_unica}")
        limpadores = st.checkbox("Limpadores de para-brisa", key=f"ch_limp_{chave_unica}")
        
    with col2:
        st.write("**💡 Iluminação & Elétrica**")
        farois = st.checkbox("Faróis e Lanternas funcionando", key=f"ch_farol_{chave_unica}")
        setas = st.checkbox("Setas e Alerta", key=f"ch_setas_{chave_unica}")
        painel = st.checkbox("Sem luzes de erro no painel", key=f"ch_painel_{chave_unica}")
        
    with col3:
        st.write("**📄 Segurança & Documentos**")
        doc = st.checkbox("Documento do veículo (CRLV) presente", key=f"ch_doc_{chave_unica}")
        ferramentas = st.checkbox("Macaco, chave de roda e triângulo", key=f"ch_ferram_{chave_unica}")
        higienizacao = st.checkbox("Interior limpo e higienizado", key=f"ch_hig__{chave_unica}")
        
    observacoes = st.text_area("Observações adicionais do estado do veículo", placeholder="Caso haja riscos, amassados ou itens faltando, detalhe aqui...", key=f"obs_{chave_unica}")
    
    # Retorna um dicionário com o status para salvar no banco se necessário
    todos_ok = all([pneus, avarias, limpadores, farois, setas, painel, doc, ferramentas, higienizacao])
    return todos_ok, observacoes

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

# --- 4. REGISTRAR ABASTECIMENTO (LANÇAMENTO MANUAL DEFINITIVO) ---
elif menu == "⛽ Importar TicketLog":  # Mantenha o texto exato que está na sua lista do sidebar
    st.title("⛽ Registrar Abastecimento Manual")
    st.markdown("Insira os dados do abastecimento realizado para atualização do histórico e odômetro da frota.")
    
    # Criando o formulário estruturado e limpo
    with st.form("form_abastecimento_manual", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            placa_manual = st.text_input("Placa do Veículo", placeholder="Ex: SYN0J10", max_chars=7).upper().strip()
            data_manual = st.date_input("Data do Abastecimento")
            km_manual = st.number_input("Odômetro / KM Registrado", min_value=0, step=1, help="Insira o KM atual marcado no painel do carro.")
        
        with col2:
            litros_manual = st.number_input("Quantidade de Litros (L)", min_value=0.0, step=0.01, format="%.2f")
            valor_manual = st.number_input("Valor Total Pago (R$)", min_value=0.0, step=0.01, format="%.2f")
            cartao_manual = st.text_input("Nº Cartão / Identificador (Opcional)", placeholder="Ex: TicketLog Frotas")
        
        # Botão oficial do Streamlit para submissão de formulários
        botao_salvar = st.form_submit_button(label="💾 Gravar Abastecimento")
        
        if botao_salvar:
            # Validação rápida dos campos obrigatórios
            if not placa_manual or len(placa_manual) < 7:
                st.error("❌ Por favor, digite uma placa válida com 7 caracteres.")
            elif litros_manual <= 0 or valor_manual <= 0:
                st.error("❌ O valor total e a quantidade de litros precisam ser maiores que zero.")
            else:
                try:
                    # Converte a data selecionada para o formato de texto DD/MM/AAAA usado no seu banco
                    data_formatada = data_manual.strftime("%d/%m/%Y")
                    identificador_origem = cartao_manual if cartao_manual else "Manual"
                    
                    # 1. Insere o registro na tabela de abastecimentos
                    query_db('''INSERT INTO abastecimentos (placa, data, litro, valor_total, km_registro, cartao) 
                                VALUES (?, ?, ?, ?, ?, ?)''', 
                             (placa_manual, data_formatada, float(litros_manual), float(valor_manual), float(km_manual), identificador_origem), 
                             is_select=False)
                    
                    # 2. Atualiza o KM atual do veículo na tabela principal (apenas se o novo KM for maior)
                    query_db("UPDATE veiculos SET km_atual = ? WHERE placa = ? AND km_atual < ?", 
                             (float(km_manual), placa_manual, float(km_manual)), is_select=False)
                    
                    st.success(f"🎉 Abastecimento do veículo **{placa_manual}** gravado com sucesso e odômetro atualizado!")
                except Exception as e:
                    st.error(f"Erro ao salvar no banco de dados: {e}")
            
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
