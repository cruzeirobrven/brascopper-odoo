---
tags: [odoo, setup]
created: 2026-06-30
---

# Odoo 18 — Setup

## Servidor
- URL: http://100.119.223.92:8069
- SO: Linux (Ubuntu)
- Path: `/opt/odoo`

## PostgreSQL
- Host: 100.119.223.92
- Database: `odoo18`
- User: `postgres`
- Password: `MULETA`

## Módulos Instalados
- `mrp` — Manufacturing / BOM
- `stock` — Inventário
- `sale` — Vendas
- `purchase` — Compras
- `account` — Contabilidade

## Categorias de Produto
- ID 1 = "All" (categoria padrão)
- Produtos técnicos: type = `product` (estocável)
- Produtos comerciais consumíveis: type = `consu`

## Uso
```bash
# Conectar ao banco
PGPASSWORD=MULETA psql -U postgres -h 100.119.223.92 -d odoo18

# Executar script de migração
python3 scripts/migracao/migrar_para_variantes.py
```

## Ações Rápidas (URLs)
- Lista de produtos: `web#action=292`
- Lista de BOMs: `web#action=489`
- Produto 001.005: `web#model=product.template&id=172520`
