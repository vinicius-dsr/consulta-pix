# Consulta Pix

Sistema de consulta de chaves Pix utilizando a API v3 do Asaas.

## Funcionalidades

- Identificação automática do tipo de chave Pix (CPF, CNPJ, E-mail, Telefone ou EVP)
- Consulta de dados do titular (nome, documento, banco, tipo de conta)
- Suporte a entrada com ou sem formatação

## Requisitos

- Python 3.7+
- Chave de API do Asaas (produção ou sandbox)

## Instalação

1. Clone o repositório:

```bash
git clone https://github.com/vinicius-dsr/consulta-pix.git
cd consulta-pix
```

2. Crie e ative o ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Crie o arquivo `.env` na raiz do projeto:

```env
ASAAS_API_URL=https://api.asaas.com/v3
ASAAS_API_KEY=sua_chave_de_api_aqui
```

## Uso

```bash
python consulta_pix.py
```

Digite a chave Pix (CPF, CNPJ, e-mail ou telefone) e pressione Enter. Digite `sair` para encerrar.
