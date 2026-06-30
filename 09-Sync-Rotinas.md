---
tags: [brascopper, sync, rotinas, agendamento]
created: 2026-06-08
---

# Rotinas de Sincronização — PDD

Todas as sincronizações são Django management commands. Podem ser rodados
manualmente, ou automaticamente via **Task Scheduler do Windows** a cada 5 minutos
usando o orquestrador `sync_all`.

---

## Orquestrador — `sync_all`

Arquivo: `core/management/commands/sync_all.py`

Executa todos os syncs em sequência. Um passo com erro não interrompe os seguintes.

```powershell
# Execução completa
py manage.py sync_all

# Pular arquivos DBF (mais rápido quando DBF não mudou)
py manage.py sync_all --skip-dbf

# Pular imports do SQL Server
py manage.py sync_all --skip-sqlserver

# Rodar apenas passos específicos
py manage.py sync_all --step sync_comercial_dbf import_sqlserver_romaneio
```

### Sequência padrão

| Ordem | Comando | Descrição |
|-------|---------|-----------|
| 1 | `sync_comercial_dbf` | Pedidos e faturas do DBF Harbour → PG |
| 2 | `import_sqlserver_expedicao --table all` | VENPED + VENITN → PG |
| 3 | `import_sqlserver_romaneio --table all` | MRPEXP + MRPROM → PG |
| 4 | `import_sqlserver_cadastros --table clientes` | CADCLI → PG |
| 5 | `import_sqlserver_financeiro` | Financeiro SQL Server → PG |
| 6 | `import_sqlserver_compras` | Compras SQL Server → PG |

---

## Logs

| Arquivo | Conteúdo |
|---------|----------|
| `logs/sync_all.log` | Log estruturado do `sync_all` (RotatingFileHandler, máx 5 MB, 5 rotações) |
| `logs/sync_scheduler.log` | stdout/stderr do bat rodado pelo Task Scheduler |

Formato de linha do `sync_all.log`:
```
2026-06-08 10:05:00 | INFO  | INICIO sync_all
2026-06-08 10:05:00 | INFO  |   START [sync_comercial_dbf] — DBF pedidos/faturas → PG
2026-06-08 10:05:03 | INFO  |   OK    [sync_comercial_dbf] 3.2s
2026-06-08 10:05:07 | INFO  |   ERRO  [import_sqlserver_financeiro] 0.1s — connection timeout
2026-06-08 10:05:07 | INFO  | FIM sync_all 7.1s — 1 erro(s): import_sqlserver_financeiro
```

A pasta `logs/` está no `.gitignore` — os arquivos não são versionados.

---

## Task Scheduler (Windows) — a cada 5 minutos

Script bat: `sync_all.bat` (raiz do projeto)

```bat
@echo off
cd /d D:\BRASC\PRG\06082025\pdd
call venv_django\Scripts\activate.bat
py manage.py sync_all >> logs\sync_scheduler.log 2>&1
```

### Registrar a tarefa (PowerShell como Administrador)

```powershell
$bat = "D:\BRASC\PRG\06082025\pdd\sync_all.bat"
$taskName = "BrascopperSyncAll"

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$bat`""

$trigger = New-ScheduledTaskTrigger `
    -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes 5) `
    -RepetitionDuration ([TimeSpan]::MaxValue)

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 4) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -RunLevel Highest -Force
```

Configurações relevantes:
- **ExecutionTimeLimit 4 min** — se um sync travar, o processo é encerrado antes da próxima rodada
- **MultipleInstances IgnoreNew** — se a rodada anterior ainda estiver rodando, a nova é ignorada (sem acúmulo)
- **StartWhenAvailable** — se o PC estava desligado no horário agendado, roda assim que ligar

### Gerenciar via PowerShell

```powershell
# Ver status
Get-ScheduledTask -TaskName BrascopperSyncAll | Select-Object State, LastRunTime, LastTaskResult

# Rodar agora manualmente
Start-ScheduledTask -TaskName BrascopperSyncAll

# Desabilitar temporariamente
Disable-ScheduledTask -TaskName BrascopperSyncAll

# Remover
Unregister-ScheduledTask -TaskName BrascopperSyncAll -Confirm:$false
```

`LastTaskResult = 0` = sucesso. Qualquer outro valor indica erro — verificar `logs/sync_scheduler.log`.

---

## Comandos individuais de referência

### DBF Harbour → PostgreSQL

```powershell
# Pedidos de venda, faturas, itens (pedido.dbf / itped.dbf / fatura.dbf)
py manage.py sync_comercial_dbf

# Tabelas legado completas (item, client, fornec, financeiro DBF, etc.)
py manage.py sync_legacydbf_raw
```

`sync_legacydbf_raw` é mais pesado (roda dump Node.js para cada tabela). Não está
no ciclo de 5 minutos por padrão — rodar sob demanda ou em agendamento separado (ex: horário).

### SQL Server → PostgreSQL

```powershell
# Pedidos e itens de venda (VENPED / VENITN)
py manage.py import_sqlserver_expedicao --table all
py manage.py import_sqlserver_expedicao --table pedidos
py manage.py import_sqlserver_expedicao --table itens

# Expedição e romaneios MRP (MRPEXP / MRPEX1 / MRPROM / MRPRO1 / MRPR1D)
py manage.py import_sqlserver_romaneio --table all
py manage.py import_sqlserver_romaneio --table exp   # só MRPEXP
py manage.py import_sqlserver_romaneio --table rom   # só MRPROM

# Cadastros (CADCLI, produtos, fornecedores, composição)
py manage.py import_sqlserver_cadastros                        # todos
py manage.py import_sqlserver_cadastros --table clientes

# Financeiro
py manage.py import_sqlserver_financeiro

# Compras
py manage.py import_sqlserver_compras

# Fiscal (pesado — rodar sob demanda)
py manage.py import_sqlserver_fiscal
py manage.py import_sqlserver_fat

# Custos
py manage.py sync_cus_postgres
```

---

## Sincronização Harbour → SQL Server VENPED

Empurra pedidos do Harbour (pedido.dbf) para a tabela VENPED do SQL Server.

```powershell
# Visualizar o que seria sincronizado (sem gravar)
py manage.py push_harbour_to_venped --preview

# Sincronizar todos os pedidos a partir de uma data
py manage.py push_harbour_to_venped --desde 2024-01-01

# Sincronizar pedido específico
py manage.py push_harbour_to_venped --pedido 127413

# Só cabeçalho, sem itens
py manage.py push_harbour_to_venped --sem-itens
```

Arquivo: `expedicao/management/commands/push_harbour_to_venped.py`

### Mapeamento de campos Harbour → VENPED

| Campo VENPED | Origem Harbour |
|-------------|----------------|
| `PEDIDO` | `int(PedidoVenda.numero)` |
| `CLIENTE` | `int(ClienteCadastro.fcod)` |
| `EMPRESA` | filial `0001` → `1` |
| `EMISSAO` | `PedidoVenda.data` |
| `TGERAL` | `PedidoVenda.valor_total` |
| `TPRODUTO` | `PedidoVenda.total_itens` |
| `PS_LIQUIDO` | `PedidoVenda.peso_total` |
| `REGISTRO` | lido de `AUTOREG WHERE TABELA='VENPED'` |

Código do produto: `ErpProduto.it_bi` ↔ `it_co` Harbour (mapeamento por best-effort).

---

## Diagnóstico rápido

```powershell
# Ver últimas linhas do log
Get-Content logs\sync_all.log -Tail 50

# Filtrar só erros
Select-String "ERRO" logs\sync_all.log | Select-Object -Last 20

# Ver quando rodou a última vez com sucesso
Select-String "FIM sync_all" logs\sync_all.log | Select-Object -Last 5
```
