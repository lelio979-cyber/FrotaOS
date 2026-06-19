import sqlite3
import csv
import customtkinter as ctk
from tkinter import messagebox

# === CONFIGURAÇÃO DO BANCO DE DADOS ===
def inicializar_banco():
    conn = sqlite3.connect('gestao_frotas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            placa TEXT PRIMARY KEY, modelo TEXT, trecho_atual TEXT, km_atual INTEGER, status TEXT DEFAULT 'Disponível', km_proxima_revisao INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT, placa TEXT, tipo_movimentacao TEXT, km INTEGER, combustivel TEXT, data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT, placa TEXT, tipo_manutencao TEXT, descricao TEXT, custo REAL, status TEXT DEFAULT 'Aguardando Aprovação'
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT, placa TEXT, tipo_custo TEXT, valor REAL, data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Inserir veículo de teste se a base estiver vazia
    cursor.execute("SELECT COUNT(*) FROM veiculos")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO veiculos VALUES ('BRA2E19', 'Volvo FH 540', 'Rota SP-RJ', 98000, 'Disponível', 100000)")
    conn.commit()
    conn.close()

inicializar_banco()

# === INTERFACE DO SISTEMA ===
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class AppFrotas(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FleetX - Gestão de Frota Profissional")
        self.geometry("1100x650")
        self.mostrar_tela_login()

    def limpar_janela(self):
        for widget in self.winfo_children():
            widget.destroy()

    def mostrar_tela_login(self):
        self.limpar_janela()
        frame_login = ctk.CTkFrame(self, width=350, height=400, corner_radius=15)
        frame_login.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl = ctk.CTkLabel(frame_login, text="FleetX Control", font=("Arial", 28, "bold"), text_color="#1F6AA5")
        lbl.pack(pady=30)
        
        btn_op = ctk.CTkButton(frame_login, text="Entrar como Operador (Campo)", height=40, fg_color="#2b2b2b", command=lambda: self.carregar_sistema("operador"))
        btn_op.pack(pady=15, padx=20, fill="x")
        
        btn_gestor = ctk.CTkButton(frame_login, text="Entrar como Gestor (Completo)", height=40, command=lambda: self.carregar_sistema("gestor"))
        btn_gestor.pack(pady=15, padx=20, fill="x")

    def carregar_sistema(self, perfil):
        self.perfil = perfil
        self.limpar_janela()
        
        # Menu Lateral
        self.menu_lateral = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu_lateral.pack(side="left", fill="y")
        
        lbl_logo = ctk.CTkLabel(self.menu_lateral, text="FleetX v1.0", font=("Arial", 20, "bold"))
        lbl_logo.pack(pady=20)
        
        # Container de Conteúdo (Onde as páginas abrem)
        self.area_conteudo = ctk.CTkFrame(self, corner_radius=15)
        self.area_conteudo.pack(side="right", fill="both", expand=True, padx=20, text_color="white", pady=20)
        
        # Botões do Menu
        btn_chk = ctk.CTkButton(self.menu_lateral, text="📋 Checklist de Campo", anchor="w", command=self.tela_checklist)
        btn_chk.pack(pady=8, padx=15, fill="x")
        
        if self.perfil == "gestor":
            btn_os = ctk.CTkButton(self.menu_lateral, text="🛠️ OS & Manutenções", anchor="w", command=self.tela_ordens_servico)
            btn_os.pack(pady=8, padx=15, fill="x")
            
            btn_fin = ctk.CTkButton(self.menu_lateral, text="💰 Custos & Relatórios", anchor="w", command=self.tela_financeiro)
            btn_fin.pack(pady=8, padx=15, fill="x")
            
        btn_sair = ctk.CTkButton(self.menu_lateral, text="🚪 Sair", fg_color="#8B0000", command=self.mostrar_tela_login)
        btn_sair.pack(side="bottom", pady=20, padx=15, fill="x")
        
        self.tela_checklist()

    def limpar_area_conteudo(self):
        for widget in self.area_conteudo.winfo_children():
            widget.destroy()

    def tela_checklist(self):
        self.limpar_area_conteudo()
        ctk.CTkLabel(self.area_conteudo, text="Checklist de Entrada e Saída", font=("Arial", 24, "bold")).pack(pady=15)
        
        frame = ctk.CTkFrame(self.area_conteudo)
        frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(frame, text="Placa do Veículo:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_placa = ctk.CTkEntry(frame, placeholder_text="Ex: BRA2E19")
        entry_placa.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="Tipo de Movimentação:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        cb_tipo = ctk.CTkComboBox(frame, values=["Entrada de Oficina", "Saída de Oficina", "Devolução", "Substituição"])
        cb_tipo.grid(row=1, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame, text="KM Atual:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        entry_km = ctk.CTkEntry(frame, placeholder_text="Ex: 98200")
        entry_km.grid(row=2, column=1, padx=10, pady=10)
        
        def salvar():
            conn = sqlite3.connect('gestao_frotas.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO checklists (placa, tipo_movimentacao, km) VALUES (?,?,?)", (entry_placa.get().upper(), cb_tipo.get(), entry_km.get()))
            cursor.execute("UPDATE veiculos SET km_atual = ? WHERE placa = ?", (entry_km.get(), entry_placa.get().upper()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Checklist Salvo! KM do veículo atualizado.")
            self.tela_checklist()

        ctk.CTkButton(frame, text="Salvar Checklist", fg_color="green", command=salvar).grid(row=3, column=0, columnspan=2, pady=20)

    def tela_ordens_servico(self):
        self.limpar_area_conteudo()
        ctk.CTkLabel(self.area_conteudo, text="Gerenciador de OS (Ordens de Serviço)", font=("Arial", 24, "bold")).pack(pady=15)
        
        frame = ctk.CTkFrame(self.area_conteudo)
        frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        ctk.CTkLabel(frame, text="Placa do Veículo:").grid(row=0, column=0, padx=10, pady=5)
        entry_p = ctk.CTkEntry(frame)
        entry_p.grid(row=0, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(frame, text="Custo Estimado (R$):").grid(row=1, column=0, padx=10, pady=5)
        entry_c = ctk.CTkEntry(frame)
        entry_c.grid(row=1, column=1, padx=10, pady=5)
        
        def criar_os():
            conn = sqlite3.connect('gestao_frotas.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO ordens_servico (placa, custo) VALUES (?,?)", (entry_p.get().upper(), entry_c.get()))
            cursor.execute("UPDATE veiculos SET status = 'Em Manutenção' WHERE placa = ?", (entry_p.get().upper(),))
            # Lança também no financeiro da operação
            cursor.execute("INSERT INTO financeiro (placa, tipo_custo, valor) VALUES (?, 'Manutenção', ?)", (entry_p.get().upper(), entry_c.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("OS Criada", "Veículo alterado para 'Em Manutenção' automaticamente!")
            self.tela_ordens_servico()

        ctk.CTkButton(frame, text="Abrir Ordem de Serviço", command=criar_os).grid(row=2, column=0, columnspan=2, pady=20)

    def tela_financeiro(self):
        self.limpar_area_conteudo()
        ctk.CTkLabel(self.area_conteudo, text="Painel Financeiro e Relatórios", font=("Arial", 24, "bold")).pack(pady=15)
        
        conn = sqlite3.connect('gestao_frotas.db')
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(valor) FROM financeiro")
        total = cursor.fetchone()[0] or 0.0
        conn.close()
        
        card = ctk.CTkFrame(self.area_conteudo, width=300, height=100, fg_color="#1f2937")
        card.pack(pady=20)
        ctk.CTkLabel(card, text="Custo Total da Operação", font=("Arial", 14, "gray")).pack(pady=5)
        ctk.CTkLabel(card, text=f"R$ {total:,.2f}", font=("Arial", 22, "bold"), text_color="#10B981").pack(pady=5)

        def exportar():
            conn = sqlite3.connect('gestao_frotas.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM checklists")
            dados = cursor.fetchall()
            with open("relatorio_checklists.csv", "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Placa", "Tipo", "KM", "Data"])
                writer.writerows(dados)
            conn.close()
            messagebox.showinfo("Exportador", "Relatório de Checklists salvo como 'relatorio_checklists.csv'!")

        ctk.CTkButton(self.area_conteudo, text="📥 Exportar Dados para Excel (.CSV)", command=exportar).pack(pady=20)

if __name__ == "__main__":
    app = AppFrotas()
    app.mainloop()
