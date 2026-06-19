import sqlite3
import csv
from tkinter import messagebox

# Dicionário solicitado para autocompletar multas
DICIONARIO_MULTAS = {
    "7455-0": {"gravidade": "Média", "pontos": 4, "valor": 130.16, "desc": "Velocidade superior à máxima em até 20%"},
    "7463-0": {"gravidade": "Grave", "pontos": 5, "valor": 195.23, "desc": "Velocidade superior à máxima entre 20% e 50%"},
    "5010-0": {"gravidade": "Gravíssima", "pontos": 7, "valor": 880.41, "desc": "Dirigir sem CNH ou com CNH vencida"}
}

def checar_alertas_revisao():
    """Retorna uma lista de veículos que atingiram ou estão perto do KM de revisão"""
    conn = sqlite3.connect('gestao_frotas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT placa, km_atual, km_proxima_revisao FROM veiculos")
    veiculos = cursor.fetchall()
    conn.close()
    
    alertas = []
    for placa, km, proxima in veiculos:
        if (proxima - km) <= 1000: # Alerta emitido faltando 1.000 km para o limite
            alertas.append(f"⚠️ REVISÃO: Veículo {placa} precisa de troca de óleo/revisão (KM: {km})")
    return alertas

def exportar_financeiro_csv():
    """Exporta todos os custos da operação para uma planilha Excel/CSV"""
    conn = sqlite3.connect('gestao_frotas.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM financeiro")
    dados = cursor.fetchall()
    conn.close()
    
    with open("relatorio_financeiro_frota.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["ID", "Placa", "Tipo de Custo", "Valor (R$)", "Data"])
        escritor.writerows(dados)
    
    messagebox.showinfo("Exportação", "Relatório Financeiro exportado para 'relatorio_financeiro_frota.csv'!")
