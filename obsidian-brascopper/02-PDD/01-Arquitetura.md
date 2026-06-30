---
tags: [pdd, django, arquitetura]
created: 2026-06-30
---

# PDD — Arquitetura

## Stack
| Camada | Tecnologia |
|--------|-----------|
| Hub web | Django 4.2 + PostgreSQL |
| ERP operacional | Delphi + SQL Server `BRVEN_BRASCOPPER` |
| Legado fábrica | Harbour/CGI + arquivos DBF |
| Frontend | Bootstrap 5 |

## Fluxo de Dados
```
DBF (Harbour) → PostgreSQL (nfehub)
SQL Server (ERP) → PostgreSQL (nfehub)
PostgreSQL (nfehub) → Django PDD (:8800)
XMLs NF-e → SQL Server (ERP)
```

## Servidor
- Windows: `100.98.13.77`
- Projeto: `D:\BRASC\PRG\06082025\pdd\`
- Porta: 8800
- Acesso remoto: `http://100.119.223.92:8800`

## Conexões
```
# PostgreSQL (nfehub)
Host: localhost (Windows) ou 100.119.223.92 (Linux)
DB: brascopper_pdd (Windows) / nfehub (Linux)
User: nfehub
Pass: nfehub123

# SQL Server ERP
Server: DESKTOP-M2UK50B\SQL2022
DB: BRVEN_BRASCOPPER
User: sa
```

## Sincronização
- Orchestrador: `sync_all` (management command)
- Execução: Task Scheduler Windows a cada 5 min
- Logs: `logs/sync_all.log`

## Apps Django
| App | Função |
|-----|--------|
| core | Filiais, produtos, clientes, sync |
| comercial | Pedidos venda, faturas, APR |
| custos | Análise mensal de custos |
| precificacao | Pricing e margem (80%) |
| producao | ItemTecnico, famílias, composições |
| financeiro | Contas a pagar/receber |
| cadastros | CADCLI, CADFOR, ESTPRO |
| suprimentos | Compras, pedidos |
| recebimentos | COMNOT, XML NF-e |
| expedicao | VENPED, MRPROM |
