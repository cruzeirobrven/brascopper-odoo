---
tags: [agente, integracao, odoo, pdd]
created: 2026-06-30
---

# Agente — Integração Odoo ↔ PDD

## Cenário Atual
- **Odoo**: Linux (100.119.223.92:8069) — produtos, BOMs, MRP
- **PDD**: Windows (100.98.13.77:8800) — custos, margem, sincronização ERP
- **nfehub**: PostgreSQL (100.119.223.92) — dados espelho do ERP

## Fluxos de Integração

### 1. Custo ← PDD (prioritário)
PDD calcula custo MP → atualiza `standard_price` no Odoo

### 2. Produtos → Odoo
Novos produtos do ERP (ESTPRO) → criar automaticamente no Odoo

### 3. Preços de Venda ← PDD
Tabela de preços calculada no PDD → `product_pricelist_item` no Odoo

### 4. Pedidos de Venda → PDD
Pedidos criados no Odoo → exportar para o ERP via PDD

## Arquitetura Sugerida
```
ERP Brascopper (Delphi/SQL Server)
  │
  ▼
PDD (Django) ─── sync_all (5 min) ───→ nfehub (PG)
  │                                        │
  │                                        ▼
  └── API REST (:8800/api/) ──────→ Agente Sync (Linux)
                                          │
                                          ▼
                                      Odoo 18 (PG)
```

## Tecnologia de Integração
- **API REST**: PDD expõe endpoints JSON, script Python consome
- **jsonrpc**: Odoo tem API jsonrpc nativa (porta 8069)
- **DB Link**: Acesso direto ao PostgreSQL (mais simples, menos seguro)

## Próximos Passos
1. ✅ BOMs migradas (5.672)
2. ✅ Variantes migradas (5.887)
3. 🔲 Criar API de custos no PDD
4. 🔲 Criar script de sync custos → Odoo
5. 🔲 Agendar cron de atualização
6. 🔲 Webhooks para eventos em tempo real
