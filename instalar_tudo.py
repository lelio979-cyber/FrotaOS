import subprocess
import sys

def instalar(biblioteca):
    print(f"Instalando {biblioteca}... Por favor, aguarde.")
    subprocess.check_call([sys.executable, "-m", "pip", "install", biblioteca])
    print(f"{biblioteca} instalada com sucesso!\n")

# O próprio Python vai tentar instalar para você sem precisar do terminal
try:
    instalar("customtkinter")
    instalar("matplotlib")
    print("🎉 TUDO PRONTO! Agora você pode rodar o sistema de frotas.")
except Exception as e:
    print(f"Ocorreu um erro na instalação automática: {e}")
