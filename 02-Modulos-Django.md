---
tags: [brascopper, django, modulos]
created: 2026-06-07
---

# Módulos Django — Status

## Apps em `INSTALLED_APPS`

| App | Status | Fonte de dados | Observação |
|-----|--------|---------------|-----------|
| `core` | ✅ | PostgreSQL + DBF | Filiais, produtos, clientes, sync legado |
| `comercial` | ✅ | PostgreSQL + SQL Server | Pedidos de venda, faturas, APR |
| `custos` | ✅ | PostgreSQL + DBF | Análise mensal de custos |
| `precificacao` | 🚧 80% | Excel + SQL Server | Importações em andamento |
| `producao` | ✅ | PostgreSQL | ItemTecnico, famílias, composições |
| `legacydbf` | ✅ | DBF | Leitura direta de arquivos .dbf |
| `financeiro` | ✅ 90% | SQL Server | PAGDUP/PAGPAG (AP), RECDUP/RECREC (AR) |
| `cadastros` | ✅ 80% | SQL Server + DBF | Reconciliação bidirecional CADCLI/CADFOR/ESTPRO |
| `suprimentos` | ✅ | SQL Server | COMPED, COMITC, COMITN, COMFIN — [[06-Suprimentos-Pedidos]] |
| `recebimentos` | ✅ | SQL Server + PG | COMNOT, COMCIT, COMEIT, COMNSE, COMNFI — [[04-Recebimentos-NF]] |
| `expedicao` | ✅ | SQL Server + DBF | VENPED, VENITN, MRPEXP/EX1/ROM/RO1/R1D — [[08-Expedicao-MRPROM]] |
| `planejamento` | ❌ | — | Comentado em settings.py |
| `contabilidade` | ❌ | — | Comentado em settings.py |

## Padrão de importação

Todos os módulos que espelham dados do ERP usam:
- Management command `import_sqlserver_<modulo>.py`
- Conexão via `_conn()` em `settings.SQLSERVER_ERP`
- Chunked `bulk_create` com deduplicação

```python
# Padrão de conexão
c = settings.SQLSERVER_ERP
cn = pyodbc.connect(
    f"DRIVER={{{c['driver']}}}; SERVER={c['server']}; DATABASE={c['database']}; ..."
)
```

## URLs base

| App | URL prefix |
|-----|-----------|
| core | `/` |
| suprimentos | `/suprimentos/` |
| recebimentos | `/recebimentos/` |
| financeiro | `/financeiro/` |
| cadastros | `/cadastros/` |
