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


def enriquecer_dados_cnpj(cnpj):
    """
    Busca dados cadastrais completos do CNPJ na BrasilAPI (sem necessidade de token).
    """
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    
    print(f"\n{CIANO}=== ENRIQUECIMENTO CNPJ (BRASILAPI) ==={RESET}")
    
    try:
        resposta = cliente.get(url)
        
        if resposta.status_code == 200:
            dados = resposta.json()
            print(f"{BOLD}Razão Social:{RESET} {dados.get('razao_social', 'Não informado')}")
            print(f"{BOLD}Nome Fantasia:{RESET} {dados.get('nome_fantasia', 'Não informado') or 'Não informado'}")
            print(f"{BOLD}Situação Cadastral:{RESET} {dados.get('descricao_situacao_cadastral', dados.get('situacao', 'Não informado'))}")
            print(f"{BOLD}Data de Abertura:{RESET} {dados.get('data_inicio_atividade', 'Não informado')}")
            print(f"{BOLD}Porte:{RESET} {dados.get('porte', 'Não informado')}")
            natureza = dados.get('natureza_juridica')
            if isinstance(natureza, dict):
                print(f"{BOLD}Natureza Jurídica:{RESET} {natureza.get('descricao', natureza.get('codigo', 'Não informado'))}")
            else:
                print(f"{BOLD}Natureza Jurídica:{RESET} {natureza or 'Não informado'}")
            cnae = dados.get('cnae_fiscal_descricao') or ""
            print(f"{BOLD}CNAE Principal:{RESET} {dados.get('cnae_fiscal', 'N/A')} {cnae}".rstrip())
            
            endereco = f"{dados.get('logradouro', '')} {dados.get('numero', '')} {dados.get('complemento', '')}".strip()
            print(f"{BOLD}Endereço:{RESET} {endereco or 'Não informado'} - {dados.get('bairro', 'Não informado')}")
            print(f"{BOLD}Município/UF:{RESET} {dados.get('municipio', 'Não informado')}/{dados.get('uf', 'Não informado')} (CEP: {dados.get('cep', 'N/A')})")
            
            capital = dados.get('capital_social')
            if capital is not None:
                print(f"{BOLD}Capital Social:{RESET} R$ {capital:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            else:
                print(f"{BOLD}Capital Social:{RESET} Não informado")
            
            socios = dados.get('qsa') or []
            if socios:
                print(f"{BOLD}Sócios ({len(socios)}):{RESET}")
                for socio in socios:
                    nome = socio.get('nome_socio', 'Não informado')
                    qual = socio.get('qualificacao_socio', {}).get('descricao', '')
                    print(f"  - {nome} {qual}".rstrip())
            else:
                print(f"{BOLD}Sócios:{RESET} Não informado")
            return dados
            
        elif resposta.status_code == 404:
            print(f"{VERMELHO}CNPJ não encontrado na base da BrasilAPI.{RESET}")
            return None
        else:
            print(f"{AMARELO}Aviso: BrasilAPI respondeu com status {resposta.status_code}: {resposta.text}{RESET}")
            return None
            
    except httpx.RequestError as e:
        print(f"{VERMELHO}Erro na requisição BrasilAPI: {e}{RESET}")
        return None


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
            
            documento = re.sub(r"\D", "", owner.get('cpfCnpj', ''))
            if documento and len(documento) == 14:
                enriquecer_dados_cnpj(documento)
            elif documento and len(documento) == 11:
                print(f"\n{AMARELO}CPF identificado. Não há API pública para enriquecer dados de CPF (LGPD).{RESET}")
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

