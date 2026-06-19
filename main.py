import customtkinter as ctk
from tkinter import messagebox
import sqlite3
import banco
import funcoes_auxiliares

# Inicializa o banco ao abrir o app
banco.inicializar_banco()

ctk.set_appearance_mode("Dark") # Visual Escuro solicitado
ctk.set_default_color_theme("blue")

class AppFrotas(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FleetX - Gestão e Operações de Frota")
        self.geometry("1280x720")
        
        # Iniciar na tela de login
        self.mostrar_tela_login()

    def limpar_janela(self):
        for widget in self.winfo_children():
            widget.destroy()

    def mostrar_tela_login(self):
        self.limpar_janela()
        
        frame_login = ctk.CTkFrame(self, width=350, height=450, corner_radius=15)
        frame_login.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl = ctk.CTkLabel(frame_login, text="FleetX Login", font=("Arial", 26, "bold"))
        lbl.pack(pady=30)
        
        # Botões rápidos para testes de perfil
        btn_op = ctk.CTkButton(frame_login, text="Entrar como Operador (Campo)", fg_color="#2b2b2b", 
                               command=lambda: self.carregar_sistema("operador"))
        btn_op.pack(pady=15, padx=20, fill="x")
        
        btn_gestor = ctk.CTkButton(frame_login, text="Entrar como Gestor (Completo)", 
                                   command=lambda: self.carregar_sistema("gestor"))
        btn_gestor.pack(pady=15, padx=20, fill="x")

    def carregar_sistema(self, perfil):
        self.perfil = perfil
        self.limpar_janela()
        
        # --- MENU LATERAL INTEGRADO ---
        self.menu_lateral = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.menu_lateral.pack(side="left", fill="y")
        
        lbl_logo = ctk.CTkLabel(self.menu_lateral, text="FleetX v1.0", font=("Arial", 20, "bold"), text_color="#1F6AA5")
        lbl_logo.pack(pady=20)
        
        # --- CONTAINER DINÂMICO PRINCIPAL (Onde as páginas abrem) ---
        self.area_conteudo = ctk.CTkFrame(self, corner_radius=15)
        self.area_conteudo.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Construção dos botões baseado no nível de acesso
        btn_chk = ctk.CTkButton(self.menu_lateral, text="📋 Checklist de Campo", anchor="w", command=self.tela_checklist)
        btn_chk.pack(pady=8, padx=15, fill="x")
        
        if self.perfil == "gestor":
            btn_os = ctk.CTkButton(self.menu_lateral, text="🛠️ OS & Manutenção", anchor="w", command=self.tela_ordens_servico)
            btn_os.pack(pady=8, padx=15, fill="x")
            
            btn_alertas = ctk.CTkButton(self.menu_lateral, text="⚠️ Painel de Alertas", anchor="w", command=self.tela_alertas)
            btn_alertas.pack(pady=8, padx=15, fill="x")
            
        btn_sair = ctk.CTkButton(self.menu_lateral, text="🚪 Sair", fg_color="#8B0000", command=self.mostrar_tela_login)
        btn_sair.pack(side="bottom", pady=20, padx=15, fill="x")
        
        # Abre na tela inicial padrão
        self.tela_checklist()

    def limpar_area_conteudo(self):
        for widget in self.area_conteudo.winfo_children():
            widget.destroy()

    # --- PÁGINA 1: CHECKLIST DE CAMPO (Fácil e Prático) ---
    def tela_checklist(self):
        self.limpar_area_conteudo()
        
        lbl = ctk.CTkLabel(self.area_conteudo, text="Checklist Digital de Campo", font=("Arial", 24, "bold"))
        lbl.pack(pady=15)
        
        frame_form = ctk.CTkFrame(self.area_conteudo)
        frame_form.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Inputs simplificados para tablet/celular no campo
        ctk.CTkLabel(frame_form, text="Placa do Veículo:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_placa = ctk.CTkEntry(frame_form, placeholder_text="Ex: ABC1234")
        entry_placa.grid(row=0, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="Motivo / Tipo:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        cb_tipo = ctk.CTkComboBox(frame_form, values=["Entrada de Oficina", "Saída de Oficina", "Substituição", "Devolução"])
        cb_tipo.grid(row=1, column=1, padx=10, pady=10)
        
        ctk.CTkLabel(frame_form, text="KM Atual:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        entry_km = ctk.CTkEntry(frame_form, placeholder_text="Ex: 104200")
        entry_km.grid(row=2, column=1, padx=10, pady=10)
        
        def salvar_checklist():
            conn = sqlite3.connect('gestao_frotas.db')
            cursor = conn.cursor()
            # Salva o checklist
            cursor.execute("INSERT INTO checklists (placa, tipo_movimentacao, km) VALUES (?,?,?)",
                           (entry_placa.get().upper(), cb_tipo.get(), entry_km.get()))
            # Atualiza o KM do veículo automaticamente no cadastro geral
            cursor.execute("UPDATE veiculos SET km_atual = ? WHERE placa = ?", (entry_km.get(), entry_placa.get().upper()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Sucesso", "Checklist transmitido e KM atualizado na base central!")
            self.tela_checklist()

        btn_enviar = ctk.CTkButton(frame_form, text="🚀 Transmitir para o Gestor", fg_color="green", command=salvar_checklist)
        btn_enviar.grid(row=3, column=0, columnspan=2, pady=20, padx=10, fill="x")

    # --- PÁGINA 2: ORDENS DE SERVIÇO & FLUXO DE STATUS ---
    def tela_ordens_servico(self):
        self.limpar_area_conteudo()
        lbl = ctk.CTkLabel(self.area_conteudo, text="Controle de Ordens de Serviço (OS)", font=("Arial", 24, "bold"))
        lbl.pack(pady=15)
        
        # Aqui entra a regra: Criar OS -> Sinaliza veículo em manutenção
        # Aprovar OS -> Veículo em Andamento / Concluir OS -> Disponível
        lbl_info = ctk.CTkLabel(self.area_conteudo, text="Lógicas de automações de OS integradas ao banco de dados.", text_color="gray")
        lbl_info.pack(pady=10)

    # --- PÁGINA 3: ALERTAS OPERACIONAIS ---
    def tela_alertas(self):
        self.limpar_area_conteudo()
        lbl = ctk.CTkLabel(self.area_conteudo, text="Painel de Monitoramento Preventivo", font=("Arial", 24, "bold"))
        lbl.pack(pady=15)
        
        alertas = funcoes_auxiliares.checar_alertas_revisao()
        if alertas:
            for alerta in alertas:
                lbl_al = ctk.CTkLabel(self.area_conteudo, text=alerta, text_color="orange", font=("Arial", 14, "bold"))
                lbl_al.pack(pady=5, anchor="w", padx=30)
        else:
            lbl_ok = ctk.CTkLabel(self.area_conteudo, text="✅ Nenhuma revisão por quilometragem pendente no momento.", text_color="green")
            lbl_ok.pack(pady=20)

if __name__ == "__main__":
    app = AppFrotas()
    app.mainloop()
