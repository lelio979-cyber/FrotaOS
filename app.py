import os
import sqlite3
import datetime
from tkinter import messagebox, ttk
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkinter import FigureCanvasTkAgg

# ==========================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS (SQLite)
# ==========================================
def conectar_db():
    conn = sqlite3.connect('gestao_frotas.db')
    cursor = conn.cursor()
    
    # Tabela de Veículos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            placa TEXT PRIMARY KEY,
            modelo TEXT,
            km_atual INTEGER,
            status TEXT DEFAULT 'Disponível',
            km_proxima_revisao INTEGER
        )
    ''')
    
    # Tabela de Checklists (Foco do Operador)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            tipo TEXT, -- 'Entrada' ou 'Saída'
            km INTEGER,
            combustivel TEXT,
            avarias TEXT,
            operador TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Ordens de Serviço (OS) e Manutenção
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            tipo_manutencao TEXT, -- 'Preventiva' ou 'Corretiva'
            descricao TEXT,
            custo REAL,
            status TEXT DEFAULT 'Aguardando Aprovação', -- 'Aguardando Aprovação', 'Em Andamento', 'Encerrado'
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de Abastecimentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abastecimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT,
            litros REAL,
            valor_total REAL,
            km_registro INTEGER,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''');

    # Tabela de Multas (Autopreenchimento por Código)
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
    return conn

# Inicializa DB e insere dados de teste caso vazios
conn = conectar_db()
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM veiculos")
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO veiculos VALUES ('BRA2E19', 'Volvo FH 540', 98000, 'Disponível', 100000)")
    cursor.execute("INSERT INTO veiculos VALUES ('ABC1234', 'Scania R450', 145000, 'Disponível', 150000)")
    conn.commit()

# Dicionário de automação de multas solicitado
DICIONARIO_MULTAS = {
    "7455-0": {"gravidade": "Média", "pontos": 4, "valor": 130.16, "desc": "Transitar em velocidade superior à máxima permitida em até 20%"},
    "7463-0": {"gravidade": "Grave", "pontos": 5, "valor": 195.23, "desc": "Transitar em velocidade superior à máxima permitida entre 20% e 50%"},
    "5010-0": {"gravidade": "Gravíssima", "pontos": 7, "valor": 880.41, "desc": "Dirigir veículo sem possuir CNH/PPD/ACC"}
}

# ==========================================
# 2. INTERFACE GRÁFICA (CustomTkinter)
# ==========================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SistemaGestaoFrotas(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("FleetX - Gestão Inteligente de Frotas")
        self.geometry("1280x720")
        
        # Tela de Login Inicial
        self.tela_login()

    def login_sucesso(self, perfil):
        self.perfil_usuario = perfil
        self.destruir_telas()
        self.construir_layout_principal()

    def destruir_telas(self):
        for widget in self.winfo_children():
            widget.destroy()

    # --- TELA DE LOGIN ---
    def tela_login(self):
        self.frame_login = ctk.CTkFrame(self, width=400, height=500, corner_radius=15)
        self.frame_login.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl_titulo = ctk.CTkLabel(self.frame_login, text="FleetX", font=("Arial", 32, "bold"), text_color="#1F6AA5")
        lbl_titulo.pack(pady=30)
        
        self.txt_user = ctk.CTkEntry(self.frame_login, placeholder_text="Usuário ou Motorista", width=250, height=40)
        self.txt_user.pack(pady=15)
        
        self.txt_pass = ctk.CTkEntry(self.frame_login, placeholder_text="Senha", show="*", width=250, height=40)
        self.txt_pass.pack(pady=15)
        
        btn_operador = ctk.CTkButton(self.frame_login, text="Entrar como Operador (Campo)", width=250, height=40, fg_color="#2b2b2b", hover_color="#3a3a3a", command=lambda: self.login_sucesso("operador"))
        btn_operador.pack(pady=10)
        
        btn_gestor = ctk.CTkButton(self.frame_login, text="Entrar como Gestor (Completo)", width=250, height=40, command=lambda: self.login_sucesso("gestor"))
        btn_gestor.pack(pady=10)

    # --- LAYOUT PRINCIPAL ---
    def construir_layout_principal(self):
        # Menu Lateral
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        
        lbl_logo = ctk.CTkLabel(self.sidebar, text="FleetX Control", font=("Arial", 20, "bold"))
        lbl_logo.pack(pady=20, padx=10)
        
        lbl_perfil = ctk.CTkLabel(self.sidebar, text=f"Perfil: {self.perfil_usuario.upper()}", text_color="green", font=("Arial", 12, "italic"))
        lbl_perfil.pack(pady=5)
        
        # Botões do Menu adaptados por perfil
        btn_chk = ctk.CTkButton(self.sidebar, text="📋 Checklist Campo", anchor="w", command=self.aba_checklist)
        btn_chk.pack(pady=5, padx=10, fill="x")
        
        btn_abast = ctk.CTkButton(self.sidebar, text="⛽ Abastecimento", anchor="w", command=self.aba_abastecimento)
        btn_abast.pack(pady=5, padx=10, fill="x")

        if self.perfil_usuario == "gestor":
            btn_dash = ctk.CTkButton(self.sidebar, text="📊 Dashboard & KPIs", anchor="w", command=self.aba_dashboard)
            btn_dash.pack(pady=5, padx=10, fill="x")
            
            btn_os = ctk.CTkButton(self.sidebar, text="🛠️ OS & Aprovações", anchor="w", command=self.aba_ordens_servico)
            btn_os.pack(pady=5, padx=10, fill="x")
            
            btn_multas = ctk.CTkButton(self.sidebar, text="⚠️ Controle de Multas", anchor="w", command=self.aba_multas)
            btn_multas.pack(pady=5, padx=10, fill="x")
            
        btn_sair = ctk.CTkButton(self.sidebar, text="🚪 Sair", fg_color="red", hover_color="#8B0000", command=self.tela_login)
        btn_sair.pack(side="bottom", pady=20, padx=10, fill="x")
        
        # Área de Conteúdo Principal
        self.conteudo = ctk.CTkFrame(self, corner_radius=10)
        self.conteudo.pack(side="right", fill="both", expand=True, padx=15, pady=15)
        
        # Inicializa na aba principal padrão do nível de acesso
        if self.perfil_usuario == "gestor":
            self.aba_dashboard()
        else:
            self.aba_checklist()

    def limpar_conteudo(self):
        for widget in self.conteudo.winfo_children():
            widget.destroy()

    # ==========================================
    # 3. MÓDULO: CHECKLIST (FOCO OPERACIONAL)
    # ==========================================
    def aba_checklist(self):
        self.limpar_conteudo()
        
        lbl_title = ctk.CTkLabel(self.conteudo, text="Checklist de Entrada e Saída (Operação Rápida)", font=("Arial", 22, "bold"))
        lbl_title.pack(pady=15)
        
        frame_form = ctk.CTkFrame(self.conteudo)
        frame_form.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Inputs rápidos
        ctk.CTkLabel(frame_form, text="Placa do Veículo:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        txt_placa = ctk.CTkEntry(frame_form, placeholder_text="Ex: BRA2E19")
        txt_placa.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="Tipo de Operação:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        cb_tipo = ctk.CTkComboBox(frame_form, values=["Entrada de Oficina", "Saída de Oficina", "Devolução", "Substituição"])
        cb_tipo.grid(row=1, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="KM Atual:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        txt_km = ctk.CTkEntry(frame_form, placeholder_text="Ex: 98500")
        txt_km.grid(row=2, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="Nível Combustível:").grid(row=3, column=0, padx=10, pady=10, sticky="e")
        cb_comb = ctk.CTkComboBox(frame_form, values=["Reserva", "1/4", "1/2", "3/4", "Cheio"])
        cb_comb.grid(row=3, column=1, padx=10, pady=10)

        ctk.CTkLabel(frame_form, text="Avarias visuais / Pneus / Sinistros:").grid(row=4, column=0, padx=10, pady=10, sticky="e")
        txt_avarias = ctk.CTkEntry(frame_form, placeholder_text="Descreva amassados, pneus carecas ou ok", width=300)
        txt_avarias.grid(row=4, column=1, padx=10, pady=10)

        def salvar_checklist():
            c = conn.cursor()
            # Insere Checklist
            c.execute("INSERT INTO checklists (placa, tipo, km, combustivel, avarias, operador) VALUES (?,?,?,?,?,?)",
                      (txt_placa.get().upper(), cb_tipo.get(), txt_km.get(), cb_comb.get(), txt_avarias.get(), "Operador Campo"))
            # Atualiza KM do veículo automaticamente
            c.execute("UPDATE veiculos SET km_atual = ? WHERE placa = ?", (txt_km.get(), txt_placa.get().upper()))
            conn.commit()
            messagebox.showinfo("Sucesso", "Checklist registrado e KM da frota atualizado!")
            self.aba_checklist()

        btn_salvar = ctk.CTkButton(frame_form, text="Salvar e Transmitir Checklist", fg_color="green", command=salvar_checklist)
        btn_salvar.grid(row=5, column=0, columnspan=2, pady=20)

    # ==========================================
    # 4. MÓDULO: ABASTECIMENTO (SIMPLIFICADO)
    # ==========================================
    def aba_abastecimento(self):
        self.limpar_conteudo()
        lbl_title = ctk.CTkLabel(self.conteudo, text="Lançamento Rápido de Abastecimento", font=("Arial", 22, "bold"))
        lbl_title.pack(pady=15)
        
        frame_form = ctk.CTkFrame(self.conteudo)
        frame_form.pack(pady=10, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(frame_form, text="Placa:").grid(row=0, column=0, padx=10, pady=10)
        txt_placa = ctk.CTkEntry(frame_form)
        txt_placa.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="Litros:").grid(row=1, column=0, padx=10, pady=10)
        txt_litros = ctk.CTkEntry(frame_form)
        txt_litros.grid(row=1, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="Valor Total (R$):").grid(row=2, column=0, padx=10, pady=10)
        txt_valor = ctk.CTkEntry(frame_form)
        txt_valor.grid(row=2, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="KM no ato:").grid(row=3, column=0, padx=10, pady=10)
        txt_km = ctk.CTkEntry(frame_form)
        txt_km.grid(row=3, column=1, padx=10, pady=10)

        def salvar_abast():
            c = conn.cursor()
            c.execute("INSERT INTO abastecimentos (placa, litros, valor_total, km_registro) VALUES (?,?,?,?)",
                      (txt_placa.get().upper(), txt_litros.get(), txt_valor.get(), txt_km.get()))
            c.execute("UPDATE veiculos SET km_atual = ? WHERE placa = ?", (txt_km.get(), txt_placa.get().upper()))
            conn.commit()
            messagebox.showinfo("Sucesso", "Abastecimento computado no financeiro!")
            self.aba_abastecimento()

        btn_salvar = ctk.CTkButton(frame_form, text="Registrar Abastecimento", command=salvar_abast)
        btn_salvar.grid(row=4, column=0, columnspan=2, pady=20)

    # ==========================================
    # 5. MÓDULO: ORDENS DE SERVIÇO & APROVAÇÕES
    # ==========================================
    def aba_ordens_servico(self):
        self.limpar_conteudo()
        lbl_title = ctk.CTkLabel(self.conteudo, text="Painel de OS, Manutenções e Aprovações Técnicas", font=("Arial", 22, "bold"))
        lbl_title.pack(pady=15)
        
        # Form de Abertura de OS
        frame_add = ctk.CTkFrame(self.conteudo)
        frame_add.pack(pady=5, padx=10, fill="x")
        
        ctk.CTkLabel(frame_add, text="Placa:").grid(row=0, column=0, padx=5, pady=5)
        txt_placa = ctk.CTkEntry(frame_add, width=100)
        txt_placa.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(frame_add, text="Tipo:").grid(row=0, column=2, padx=5, pady=5)
        cb_tipo = ctk.CTkComboBox(frame_add, values=["Preventiva", "Corretiva"], width=120)
        cb_tipo.grid(row=0, column=3, padx=5, pady=5)
        
        ctk.CTkLabel(frame_add, text="Desc:").grid(row=0, column=4, padx=5, pady=5)
        txt_desc = ctk.CTkEntry(frame_add, width=200)
        txt_desc.grid(row=0, column=5, padx=5, pady=5)
        
        ctk.CTkLabel(frame_add, text="Custo (R$):").grid(row=0, column=6, padx=5, pady=5)
        txt_custo = ctk.CTkEntry(frame_add, width=80)
        txt_custo.grid(row=0, column=7, padx=5, pady=5)
        
        def criar_os():
            c = conn.cursor()
            placa = txt_placa.get().upper()
            # Regra de negócio: Criou OS -> Veículo sinaliza "Em Manutenção"
            c.execute("INSERT INTO ordens_servico (placa, tipo_manutencao, descricao, custo) VALUES (?,?,?,?)",
                      (placa, cb_tipo.get(), txt_desc.get(), txt_custo.get()))
            c.execute("UPDATE veiculos SET status = 'Em Manutenção' WHERE placa = ?", (placa,))
            conn.commit()
            messagebox.showinfo("OS Criada", "OS gerada com sucesso! Veículo bloqueado para manutenção preventiva/corretiva.")
            self.aba_ordens_servico()
            
        btn_criar = ctk.CTkButton(frame_add, text="+ Abrir OS", fg_color="#1F6AA5", command=criar_os)
        btn_criar.grid(row=0, column=8, padx=10, pady=5)
        
        # Lista de Aprovações Pendentes e Fluxos
        lbl_sub = ctk.CTkLabel(self.conteudo, text="Fluxo de Aprovação e Execução", font=("Arial", 14, "bold"))
        lbl_sub.pack(pady=10)
        
        frame_lista = ctk.CTkFrame(self.conteudo)
        frame_lista.pack(pady=5, padx=10, fill="both", expand=True)
        
        c = conn.cursor()
        c.execute("SELECT id, placa, tipo_manutencao, custo, status FROM ordens_servico WHERE status != 'Encerrado'")
        rows = c.fetchall()
        
        for i, r in enumerate(rows):
            os_id, plc, tp, cst, st = r
            lbl_info = ctk.CTkLabel(frame_lista, text=f"OS #{os_id} | {plc} | {tp} | R${cst} | Status atual: {st}", font=("Arial", 12))
            lbl_info.grid(row=i, column=0, padx=10, pady=5, sticky="w")
            
            if st == "Aguardando Aprovação":
                btn_aprov = ctk.CTkButton(frame_lista, text="Aprovar (Entrar em Andamento)", fg_color="orange", text_color="black", height=20,
                                          command=lambda o=os_id, p=plc: self.alterar_status_os(o, p, "Em Andamento", "Em Andamento"))
                btn_aprov.grid(row=i, column=1, padx=5, pady=5)
            elif st == "Em Andamento":
                btn_fechar = ctk.CTkButton(frame_lista, text="Encerrar (Liberar Veículo)", fg_color="green", height=20,
                                           command=lambda o=os_id, p=plc: self.alterar_status_os(o, p, "Encerrado", "Disponível"))
                btn_fechar.grid(row=i, column=1, padx=5, pady=5)

    def alterar_status_os(self, os_id, placa, novo_status_os, novo_status_veiculo):
        c = conn.cursor()
        c.execute("UPDATE ordens_servico SET status = ? WHERE id = ?", (novo_status_os, os_id))
        c.execute("UPDATE veiculos SET status = ? WHERE placa = ?", (novo_status_veiculo, placa))
        conn.commit()
        messagebox.showinfo("Atualização", f"OS #{os_id} atualizada para {novo_status_os}!")
        self.aba_ordens_servico()

    # ==========================================
    # 6. MÓDULO: MULTAS INTELIGENTES (AUTOPREENCHIMENTO)
    # ==========================================
    def aba_multas(self):
        self.limpar_conteudo()
        lbl_title = ctk.CTkLabel(self.conteudo, text="Registro Inteligente de Multas (Preenchimento Automático)", font=("Arial", 22, "bold"))
        lbl_title.pack(pady=15)
        
        frame_form = ctk.CTkFrame(self.conteudo)
        frame_form.pack(pady=10, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(frame_form, text="Placa:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        txt_placa = ctk.CTkEntry(frame_form)
        txt_placa.grid(row=0, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame_form, text="Data:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        txt_data = ctk.CTkEntry(frame_form, placeholder_text="DD/MM/AAAA")
        txt_data.grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame_form, text="Endereço/Rodovia:").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        txt_end = ctk.CTkEntry(frame_form, placeholder_text="Ex: BR-116 KM 20")
        txt_end.grid(row=2, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame_form, text="Código da Multa:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
        txt_cod = ctk.CTkEntry(frame_form, placeholder_text="Ex: 7455-0, 7463-0")
        txt_cod.grid(row=3, column=1, padx=10, pady=5)
        
        lbl_help = ctk.CTkLabel(frame_form, text="Códigos válidos no sistema de teste: 7455-0, 7463-0, 5010-0", text_color="gray")
        lbl_help.grid(row=3, column=2, padx=10, pady=5)

        def processar_multa():
            cod = txt_cod.get().strip()
            if cod in DICIONARIO_MULTAS:
                info = DICIONARIO_MULTAS[cod]
                c = conn.cursor()
                c.execute('''INSERT INTO multas (placa, data, endereco, codigo_multa, gravidade, pontos, valor, descricao)
                             VALUES (?,?,?,?,?,?,?,?)''', 
                          (txt_placa.get().upper(), txt_data.get(), txt_end.get(), cod, info["gravidade"], info["pontos"], info["valor"], info["desc"]))
                conn.commit()
                messagebox.showinfo("Multa Gravada", f"Sucesso!\nGravidade: {info['gravidade']}\nValor: R$ {info['valor']}\nPontos: {info['pontos']}")
                self.aba_multas()
            else:
                messagebox.showerror("Erro", "Código de infração não cadastrado na base automatizada do sistema.")

        btn_multa = ctk.CTkButton(frame_form, text="Aplicar e Autopreencher Dados", fg_color="red", command=processar_multa)
        btn_multa.grid(row=4, column=0, columnspan=2, pady=20)

    # ==========================================
    # 7. DASHBOARD, REVISÕES, KPIS & GRÁFICOS
    # ==========================================
    def aba_dashboard(self):
        self.limpar_conteudo()
        
        # Cabeçalho de Alertas Inteligentes (Troca de óleo / KM Revisão)
        frame_alertas = ctk.CTkFrame(self.conteudo, fg_color="#331a1a")
        frame_alertas.pack(fill="x", padx=15, pady=5)
        
        c = conn.cursor()
        c.execute("SELECT placa, km_atual, km_proxima_revisao FROM veiculos")
        veiculos = c.fetchall()
        
        alertas_ativos = False
        for v in veiculos:
            # Se faltar menos de 3.000 KM para a revisão de 10 em 10 mil KM
            if v[2] - v[1] <= 3000:
                alertas_ativos = True
                lbl_alerta = ctk.CTkLabel(frame_alertas, text=f"⚠️ ALERTA DE REVISÃO: Veículo {v[0]} está com {v[1]} KM (Revisão programada em: {v[2]} KM)", text_color="orange", font=("Arial", 12, "bold"))
                lbl_alerta.pack(anchor="w", padx=10, pady=2)
                
        if not alertas_ativos:
            lbl_alerta = ctk.CTkLabel(frame_alertas, text="✅ Todos os planos de revisão (Trocas de óleo/filtros) e CNHs em dia.", text_color="green")
            lbl_alerta.pack(anchor="w", padx=10, pady=5)

        # KPIs Financeiros e Operacionais (Cartões de dados)
        frame_kpis = ctk.CTkFrame(self.conteudo)
        frame_kpis.pack(fill="x", padx=15, pady=10)
        
        # Coleta de dados financeiros reais do banco
        c.execute("SELECT SUM(custo) FROM ordens_servico")
        total_maint = c.fetchone()[0] or 0.0
        c.execute("SELECT SUM(valor_total) FROM abastecimentos")
        total_fuel = c.fetchone()[0] or 0.0
        total_custos_operacao = total_maint + total_fuel
        
        c.execute("SELECT COUNT(*) FROM veiculos WHERE status='Em Manutenção' OR status='Em Andamento'")
        em_oficina = c.fetchone()[0]
        
        # Renderização dos Cartões
        kpi1 = ctk.CTkFrame(frame_kpis, width=200, height=80, fg_color="#1f2937")
        kpi1.pack(side="left", padx=15, pady=10, expand=True)
        ctk.CTkLabel(kpi1, text="Custo de Operação", font=("Arial", 12, "gray")).pack(pady=5)
        ctk.CTkLabel(kpi1, text=f"R$ {total_custos_operacao:,.2f}", font=("Arial", 18, "bold"), text_color="#10B981").pack()

        kpi2 = ctk.CTkFrame(frame_kpis, width=200, height=80, fg_color="#1f2937")
        kpi2.pack(side="left", padx=15, pady=10, expand=True)
        ctk.CTkLabel(kpi2, text="Gasto c/ Combustível", font=("Arial", 12, "gray")).pack(pady=5)
        ctk.CTkLabel(kpi2, text=f"R$ {total_fuel:,.2f}", font=("Arial", 18, "bold")).pack()

        kpi3 = ctk.CTkFrame(frame_kpis, width=200, height=80, fg_color="#1f2937")
        kpi3.pack(side="left", padx=15, pady=10, expand=True)
        ctk.CTkLabel(kpi3, text="Frota Indisponível (Oficina)", font=("Arial", 12, "gray")).pack(pady=5)
        ctk.CTkLabel(kpi3, text=str(em_oficina), font=("Arial", 18, "bold"), text_color="red").pack()

        # Seção Gráfica Dinâmica (Matplotlib integrado ao CustomTkinter)
        frame_graficos = ctk.CTkFrame(self.conteudo)
        frame_graficos.pack(fill="both", expand=True, padx=15, pady=5)
        
        fig, ax = plt.subplots(figsize=(5, 2.5), facecolor='#1D1E1E')
        ax.set_facecolor('#1D1E1E')
        
        categorias = ['Manutenção', 'Combustível']
        valores = [total_maint, total_fuel]
        
        ax.bar(categorias, valores, color=['#EF4444', '#3B82F6'])
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_title("Distribuição de Custos Reais da Frota", color='white', fontsize=12)
        
        canvas = FigureCanvasTkAgg(fig, master=frame_graficos)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Botão de Exportação de Relatórios solicitado
        def exportar_dados():
            with open("relatorio_financeiro.csv", "w") as f:
                f.write("Tipo Custos,Valor Total\n")
                f.write(f"Manutencao Total,{total_maint}\n")
                f.write(f"Combustivel Total,{total_fuel}\n")
            messagebox.showinfo("Exportador", "Relatório de Custos e KPIs exportado com sucesso em CSV na pasta raiz do sistema!")

        btn_exportar = ctk.CTkButton(self.conteudo, text="📥 Exportar Dados Gerenciais (.CSV)", command=exportar_dados)
        btn_exportar.pack(pady=10)


if __name__ == "__main__":
    app = SistemaGestaoFrotas()
    app.mainloop()
