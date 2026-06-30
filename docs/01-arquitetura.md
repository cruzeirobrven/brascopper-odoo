---
tags:
  - nfe
  - arquitetura
  - hub
created: 2026-06-28
---

# Arquitetura do NF-e Hub

## Visao Geral

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              ERPs / Clientes                            │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌────────┐  ┌────────────┐  │
│  │ERP A │  │ERP B │  │ERP C │  │...   │  │Agentes │  │  Qualquer   │  │
│  │(REST)│  │(REST)│  │(REST)│  │      │  │  IA    │  │consumidor   │  │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  │(MCP)   │  │  HTTP/MCP   │  │
│     │         │         │         │       └───┬─────┘  └──────┬──────┘  │
└─────┼─────────┼─────────┼─────────┼───────────┼───────────────┼────────┘
      │         │         │         │           │               │
      ▼         ▼         ▼         ▼           ▼               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         ┌─────────────────────┐                        │
│                         │    API REST (8000)   │                        │
│                         │  FastAPI + Uvicorn   │                        │
│                         │  /api/v1/nfe/*       │                        │
│                         └──────────┬──────────┘                        │
│                                    │                                    │
│                         ┌──────────▼──────────┐                        │
│                         │   MCP Server (8001)  │                        │
│                         │   (agentes IA)      │                        │
│                         └──────────┬──────────┘                        │
│                                    │                                    │
│                         ┌──────────▼──────────┐                        │
│                         │    Gerador INI      │                        │
│                         │  (nfe_ini.py)       │                        │
│                         │  Dados → INI file   │                        │
│                         └──────────┬──────────┘                        │
│                                    │                                    │
│                         ┌──────────▼──────────┐                        │
│                         │   ACBrMonitor (TCP)  │                        │
│                         │   NFE.CriarEnviarNFe │                        │
│                         │   NFE.Consultar      │                        │
│                         │   NFE.Cancelar       │                        │
│                         │   NFE.Inutilizar     │                        │
│                         └──────────┬──────────┘                        │
│                                    │                                    │
│                                    ▼                                    │
│                              ┌──────────┐                              │
│                              │  SEFAZ   │                              │
│                              │(produção/ │                              │
│                              │homologação)│                             │
│                              └──────────┘                              │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         Fluxo Alternativo (Futuro)                      │
│                                                                         │
│  App Lazarus (ACBr Components) → ACBrLib → SEFAZ (sem ACBrMonitor)    │
└─────────────────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. API REST (FastAPI) — porta 8000
Interface principal para ERPs e sistemas externos.
- Autenticacao via API Key (JWT futuro)
- Endpoints RESTful para todas operacoes NFe
- Validacao de dados com Pydantic
- Documentacao automatica (Swagger/OpenAPI)

### 2. MCP Server — porta 8001
Interface para agentes de IA (Model Context Protocol).
- Ferramentas (tools): criar, consultar, cancelar NFe
- Recursos (resources): templates, schemas, regras
- Integracao com qualquer cliente MCP (Claude Code, Cline, etc.)

### 3. Gerador INI (Python)
Logica central de geracao do arquivo INI consumido pelo ACBrMonitor.
- Traduz dados do banco → secoes do INI
- Implementa as mesmas regras do `TFFATNFE.Criar_NFE` (Delphi)
- Validacao e calculos fiscais (ICMS, IPI, PIS, COFINS, ST, FCP, Difal)

### 4. ACBrMonitor
Software ACBr que encapsula a comunicacao com as SEFAZ.
- Recebe comandos via TCP (porta 3434)
- Gera XML, assina, transmite, consulta, cancela
- Processo separado (gestao de falhas independente)

### 5. App Lazarus (Futuro)
Aplicacao desktop para operacao manual.
- Usa componentes ACBr nativos
- Alternativa quando ACBrMonitor nao estiver disponivel
- Interface grafica completa (ja iniciada em `/opt/nferef/lazarus-nfe/`)

## Fluxo de Dados (Geracao NFe)

```
ERP → API → nfe_ini.py → arquivo INI → ACBrMonitor → SEFAZ → XML → resposta
```

### Passo a passo
1. ERP envia dados da nota para `POST /api/v1/nfe/gerar`
2. API valida com schemas Pydantic
3. `Gerador INI` monta o arquivo `.ini` com todas as secoes
4. API envia comando `NFE.CriarEnviarNFe=<caminho_ini>` via TCP ao ACBrMonitor
5. ACBrMonitor processa, assina, transmite a NFe para SEFAZ
6. ACBrMonitor retorna XML + resultado (autorizada/rejeitada/denegada)
7. API persiste resultado e retorna ao ERP

## Seguranca

- **API Key** em cada request (header `X-API-Key`)
- **Tax limiting** por cliente
- **Audit log** de todas operacoes
- **HTTPS** em producao (proxy reverso com nginx)
- Acesso ao ACBrMonitor restrito a localhost
- Certificado A1/A3 configurado no ACBrMonitor

## Tecnologias

| Componente | Tecnologia | Versao |
|-----------|-----------|--------|
| API | Python / FastAPI | 3.10+ |
| MCP | Python / mcp | latest |
| Gerador INI | Python | 3.10+ |
| Comunicacao SEFAZ | ACBrMonitor | 1.4.0+ |
| App Desktop | Lazarus / FPC | 4.8.0 / 3.2.2 |
| Banco | MSSQL (via FreeTDS/ODBC) | - |
| Documentacao | Markdown (Obsidian) | - |
