---
tags:
  - nfe
  - hub
  - api
  - mcp
  - index
created: 2026-06-28
---

# NF-e Hub — Indice da Documentacao

> Plataforma centralizada de geracao de NF-e para multiplos ERPs.
> App desktop (Lazarus) + API REST (FastAPI) + MCP Server (agentes IA).

## Documentos

| # | Documento | Descricao |
|---|-----------|-----------|
| 00 | `00-indice.md` | Este indice |
| 01 | `01-arquitetura.md` | Visao geral da arquitetura do hub |
| 02 | `02-fluxo-nfe.md` | Fluxo completo de geracao/envio NFe |
| 03 | `03-banco-dados.md` | Tabelas e campos do banco Brascopper |
| 04 | `04-acbrmonitor.md` | Configuracao do ACBrMonitor |
| 05 | `05-lazarus-app.md` | App desktop Lazarus |
| 06 | `06-api-rest.md` | API REST (FastAPI) |
| 07 | `07-mcp-server.md` | MCP Server para agentes IA |
| 08 | `08-seguranca.md` | Autenticacao, autorizacao, boas praticas |
| 09 | `09-deploy.md` | Deploy, Docker, CI/CD |
| 10 | `10-scripts-uteis.md` | Comandos e scripts do dia a dia |

## Repositorio

```
/opt/nfelazarus/          ← Workspace principal
├── docs/                 ← Documentacao Obsidian
├── api/                  ← API REST (FastAPI)
├── mcp/                  ← MCP Server
├── app/                  ← App Lazarus (futuro)
├── scripts/              ← Scripts utilitarios
├── shared/               ← Codigo compartilhado (models, helpers)
└── referencia/ → /opt/nferef  ← Fontes de referencia Brascopper

/opt/nferef/              ← Repositorio de referencia
├── docs/                 ← Docs de engenharia reversa
├── fontes/               ← Fontes Delphi originais
├── lazarus-nfe/          ← Port Lazarus inicial
└── sql/                  ← Scripts SQL

/opt/ACBrMonitor/         ← ACBrMonitor instalado
├── ACBrMonitor           ← Binario
├── ACBrMonitor.ini       ← Config
├── ACBrNFeServicos.ini   ← WS NFe
├── Logs/                 ← Logs de envio
├── Arqs/                 ← XMLs gerados
└── PDF/                  ← DANFEs gerados
```

## Status

| Componente | Status |
|------------|--------|
| ACBrMonitor | ✅ Instalado e rodando (TCP desligado) |
| Lazarus 4.8.0 / FPC 3.2.2 | ✅ Instalado |
| Python 3.10.12 | ✅ Instalado |
| Node 22.22.2 | ✅ Instalado |
| ACBrLib | ❌ Pendente download |
| Componentes ACBr Lazarus | ❌ Pendente instalacao |
| API FastAPI | ❌ Nao iniciado |
| MCP Server | ❌ Nao iniciado |

## Como usar este indice

Cada documento e um arquivo `.md` autonomo que pode ser aberto no Obsidian.
Links entre documentos usam `[[wiki-links]]` ou caminhos relativos.
