---
tags:
  - api
  - fastapi
  - rest
created: 2026-06-28
---

# API REST — FastAPI

## Visao Geral

API REST para geracao e gestao de NF-e. Projetada para ser consumida por ERPs, sistemas web e agentes de IA.

- **Base URL**: `http://localhost:8000/api/v1`
- **Documentacao**: `http://localhost:8000/docs` (Swagger)
- **Formato**: JSON

## Endpoints

### NFe

| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/nfe/gerar` | Gerar e enviar NFe |
| GET | `/nfe/{chave}` | Consultar situacao |
| POST | `/nfe/{chave}/cancelar` | Cancelar NFe |
| POST | `/nfe/inutilizar` | Inutilizar numeracao |
| POST | `/nfe/{chave}/cce` | Carta de Correcao |
| GET | `/nfe/{chave}/danfe` | Download DANFE |

### Utilitarios

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/status` | Status do servico + ACBrMonitor |
| GET | `/sefaz/status` | Status SEFAZ |

## Autenticacao

```http
X-API-Key: <api_key>
```

As chaves sao configuradas no servidor. Cada ERP/cliente tem sua propria chave.

## Exemplo de Uso

```bash
# Gerar NFe
curl -X POST http://localhost:8000/api/v1/nfe/gerar \
  -H "X-API-Key: key123" \
  -H "Content-Type: application/json" \
  -d '{
    "registro": 12345,
    "empresa": 1,
    "operacao": 101,
    "emitente": {...},
    "destinatario": {...},
    "itens": [...],
    "parcelas": [...]
  }'

# Consultar
curl http://localhost:8000/api/v1/nfe/352006... \
  -H "X-API-Key: key123"

# Cancelar
curl -X POST http://localhost:8000/api/v1/nfe/352006.../cancelar \
  -H "X-API-Key: key123" \
  -d '{"justificativa": "Erro na emissao"}'
```

## Estrutura do Projeto

```
api/
├── __init__.py
├── main.py              ← Ponto de entrada FastAPI
├── config.py            ← Configuracoes (api keys, ACBr host)
├── auth.py              ← Autenticacao (API Key)
├── routers/
│   ├── __init__.py
│   └── nfe.py           ← Rotas de NFe
├── schemas/
│   ├── __init__.py
│   ├── nfe.py           ← Pydantic models
│   └── requests.py      ← Schemas de request/response
├── services/
│   ├── __init__.py
│   ├── nfe_ini.py       ← Gerador INI (logica central)
│   └── acbr_monitor.py  ← Comunicacao TCP com ACBrMonitor
└── requirements.txt     ← Dependencias
```

## Dependencias

```
fastapi
uvicorn[standard]
pydantic
python-multipart
httpx
```
