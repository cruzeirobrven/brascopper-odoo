---
tags: [brascopper, pdd, index]
created: 2026-06-07
---

# Brascopper PDD — Índice

Hub Django de integração entre o ERP Delphi/SQL Server e o sistema legado Harbour/DBF.

## Navegação

- [[01-Arquitetura]] — Visão geral: stacks, bancos, fluxo de dados
- [[02-Modulos-Django]] — Todos os apps Django e status
- [[03-Integracao-SQL-Server]] — Como o PDD acessa o ERP Brascopper
- [[04-Recebimentos-NF]] — Módulo de recebimentos: COMNOT, COMCIT, COMEIT, COMNSE, COMNFI
- [[05-Pipeline-XML-NFe]] — Importação de XMLs NF-e: staging XMLNOT → vinculação → COMNOT
- [[06-Suprimentos-Pedidos]] — Pedidos de compra, itens, NFs vinculadas
- [[07-ERP-Tabelas-Chave]] — Referência de tabelas SQL Server usadas
- [[08-Expedicao-MRPROM]] — Módulo Expedição: pedidos de venda + romaneios MRP
- [[09-Sync-Rotinas]] — Rotinas de sincronização: sync_all, Task Scheduler, logs, comandos individuais

---
*Projeto:* `D:\BRASC\PRG\06082025\pdd\`  
*ERP SQL Server:* `BRVEN_BRASCOPPER`
