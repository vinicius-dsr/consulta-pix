import os
import re
import time
import httpx
from urllib.parse import quote
from dotenv import load_dotenv

# Ativa o suporte a cores ANSI no terminal do Windows
if os.name == 'nt':
    os.system('color')

# Definição de cores ANSI para o terminal
RESET = "\033[0m"
BOLD = "\033[1m"
VERDE = "\033[32m"
VERMELHO = "\033[31m"
AMARELO = "\033[33m"
AZUL = "\033[34m"
CIANO = "\033[36m"

# 1. Carrega as variáveis do arquivo .env
load_dotenv()

API_URL = os.getenv("ASAAS_API_URL")
API_KEY = os.getenv("ASAAS_API_KEY")

if not API_URL or not API_KEY:
    raise ValueError(f"{VERMELHO}Erro: Verifique se ASAAS_API_URL e ASAAS_API_KEY estão configurados no seu .env{RESET}")

headers = {
    "access_token": API_KEY,
    "accept": "application/json"
}

cliente = httpx.Client(http2=True, timeout=15, follow_redirects=True)

def identificar_e_filtrar_chave(chave_bruta):
    """
    Analisa a string de entrada para descobrir o tipo correto e normalizar seu formato.
    """
    chave = chave_bruta.strip()
    
    # 1. Filtro de E-mail (Possui @ e .)
    if "@" in chave and "." in chave:
        return "EMAIL", chave.lower()
    
    # Remove todos os caracteres que não forem números
    apenas_numeros = re.sub(r"\D", "", chave)
    
    if not apenas_numeros:
        return "EVP", chave
    
    # 2. Filtro de Telefone Celular (Correção da verificação do dígito 9)
    # Verifica se tem 11 dígitos e se o terceiro dígito (início do número local) é o 9
    if len(apenas_numeros) == 11 and apenas_numeros[2] == '9':
        return "PHONE", f"55{apenas_numeros}"
    elif len(apenas_numeros) == 13 and apenas_numeros.startswith("55"):
        return "PHONE", apenas_numeros
    elif chave.startswith("+"):
        valores_limpos = re.sub(r"\D", "", chave)
        return "PHONE", valores_limpos
        
    # 3. Filtro de CPF
    if len(apenas_numeros) == 11:
        return "CPF", apenas_numeros
        
    # 4. Filtro de CNPJ
    if len(apenas_numeros) == 14:
        return "CNPJ", apenas_numeros
            
    return "EVP", chave


def consultar_chave_pix(chave_para_analise):
    tipo, chave_normalizada = identificar_e_filtrar_chave(chave_para_analise)
    
    base_url = API_URL.rstrip('/')
    if "/v3" not in base_url:
        base_url = f"{base_url}/v3"
        
    tipo_codificado = quote(tipo)
    chave_codificada = quote(chave_normalizada)
    
    url_completa = f"{base_url}/pix/addressKeys/external?type={tipo_codificado}&key={chave_codificada}"
    
    print(f"\n{AZUL}[Filtro Detectado: {tipo}]{RESET} Consultando: {chave_normalizada}...")
    
    try:
        resposta = None
        for tentativa in range(1, 4):
            try:
                resposta = cliente.get(url_completa, headers=headers)
                break
            except httpx.TransportError:
                if tentativa == 3:
                    raise
                time.sleep(1)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            owner = dados.get("owner", {})
            
            print(f"{VERDE}Consulta realizada com sucesso!{RESET}")
            print(f"{BOLD}Nome do Titular:{RESET} {owner.get('name', dados.get('name', 'Não informado'))}")
            print(f"{BOLD}Documento (CPF/CNPJ):{RESET} {owner.get('cpfCnpj', dados.get('cpfCnpj', 'Não informado'))}")
            banco = dados.get('ispbName') or dados.get('financialInstitution', {}).get('bank', {}).get('name', 'Não informado')
            print(f"{BOLD}Banco:{RESET} {banco} (ISPB: {dados.get('ispb', 'N/A')})")
            inst = dados.get('financialInstitution', {})
            banco_detalhes = inst.get('bank', {})
            print(f"{BOLD}Nome do Banco:{RESET} {banco_detalhes.get('name', 'Não informado')} (Código: {banco_detalhes.get('code', inst.get('code', 'N/A'))})")
            return dados
            
        elif resposta.status_code == 400:
            print(f"{VERMELHO}Erro 400: Chave inválida ou não encontrada.{RESET}")
            return None
            
        elif resposta.status_code == 401 or resposta.status_code == 403:
            print(f"{VERMELHO}Erro de Autenticação: Chave de API inválida.{RESET}")
            return None
            
        else:
            print(f"{AMARELO}Aviso: O servidor respondeu com status {resposta.status_code}: {resposta.text}{RESET}")
            return None
            
    except httpx.RequestError as e:
        print(f"{VERMELHO}Erro na requisição: {e}{RESET}")
        return None


if __name__ == "__main__":
    print(f"{CIANO}=== SISTEMA DE CONSULTA PIX (ASAAS API v3) ==={RESET}")
    print("Digite a chave que deseja consultar ou 'sair' para encerrar.\n")
    
    while True:
        entrada = input(f"{BOLD}Digite a Chave Pix (CPF, E-mail ou Telefone):{RESET} ")
        
        if entrada.strip().lower() == 'sair':
            print(f"{AZUL}Programa encerrado.{RESET}")
            break
            
        if not entrada.strip():
            print(f"{AMARELO}Por favor, insira uma chave válida.{RESET}")
            continue
            
        consultar_chave_pix(entrada)
        print("-" * 50)

