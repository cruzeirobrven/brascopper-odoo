---
created: 2026-06-30
---

# Brascopper Odoo — Vault de Conhecimento

Hub de documentação da migração e integração entre ERP Brascopper, PDD (Django) e Odoo 18.

## Navegação

### 01 — Odoo
- [[01-Odoo/01-Setup|Setup Odoo 18]]
- [[01-Odoo/02-Migracao-BOM|Migração de BOMs]]
- [[01-Odoo/03-Migracao-Variantes|Migração de Variantes]]
- [[01-Odoo/04-Estrutura-Produtos|Estrutura de Produtos]]

### 02 — PDD (Django)
- [[02-PDD/01-Arquitetura|Arquitetura PDD]]
- [[02-PDD/02-Pricing-Custos|Pricing e Custos]]
- [[02-PDD/03-API-Endpoints|API Endpoints]]

### 03 — Agentes de Integração
- [[03-Agentes/01-Sync-Custos|Sync de Custos Odoo ← PDD]]
- [[03-Agentes/02-Integracao-Odoo-PDD|Integração Odoo ↔ PDD]]
- [[03-Agentes/03-ETL-BOM|ETL de BOMs]]

### 04 — Bancos de Dados
- [[04-Banco-Dados/01-Odoo-PG|Odoo PostgreSQL]]
- [[04-Banco-Dados/02-Nfehub-PG|Nfehub PostgreSQL]]
- [[04-Banco-Dados/03-SQLServer-ERP|SQL Server ERP]]

### 05 — Roteiros Executados
- [[05-Roteiros/01-Criar-BOMs|Criação de BOMs]]
- [[05-Roteiros/02-Migrar-Variantes|Migração de Variantes]]

## Conexões Rápidas

| Sistema | Host | Banco | Acesso |
|---------|------|-------|--------|
| Odoo 18 | 100.119.223.92:8069 | odoo18 | postgres/MULETA |
| PDD (Django) | 100.119.223.92:8800 | nfehub | nfehub/nfehub123 |
| SQL Server ERP | 100.98.13.77 | BRVEN_BRASCOPPER | sa |
| Servidor Windows | 100.98.13.77 | — | dell/Br@214372 |

## Servidores

| Nome | IP | Função |
|------|-----|--------|
| nfelazarus | 100.119.223.92 | Odoo 18 + PDD PostgreSQL |
| Windows Server | 100.98.13.77 | ERP Delphi + SQL Server + PDD Django |
| Rede local | 192.168.10.123 | IP local do Windows |
