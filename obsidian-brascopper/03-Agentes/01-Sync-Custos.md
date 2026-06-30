---
tags: [agente, custos, integracao]
created: 2026-06-30
---

# Agente — Sync de Custos Odoo ← PDD

## Objetivo
Manter o `standard_price` dos produtos no Odoo atualizado com o custo de matéria-prima calculado pelo PDD.

## Fluxo
```
PDD (cálculo custo)
  │
  ├── Opção 1: API REST
  │     PDD expõe GET /api/precos/{codigo}
  │     Script no Linux consulta e atualiza Odoo
  │
  ├── Opção 2: Banco Direto
  │     Script Python lê tabelas do nfehub (proda.presi)
  │     e faz UPDATE no odoo18.product_template.standard_price
  │
  └── Opção 3: Push do PDD
        PDD chama API do Odoo (jsonrpc) após cada sync
```

## Tabelas Envolvidas

### nfehub (PDD)
| Tabela | Campo | Descrição |
|--------|-------|-----------|
| `legacy_proda` | `presi` | Preço atual da MP |
| `legacy_tbpro` | — | BOM (componentes) |
| `erp_produto_tecnico_mapping` | `it_px, it_co` | Mapeamento código técnico |

### odoo18
| Tabela | Campo | Descrição |
|--------|-------|-----------|
| `product_template` | `default_code`, `standard_price` | Produto + custo |
| `product_product` | `default_code`, `product_tmpl_id` | Variantes |

## Script Base
```python
#!/usr/bin/env python3
"""
Sync custos do PDD para Odoo.
Lê proda.presi do nfehub e atualiza standard_price no odoo18.
"""
import psycopg2

# Conexões
nfehub = psycopg2.connect(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')
odoo = psycopg2.connect(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')

# Busca preços do proda
cur = nfehub.cursor()
cur.execute("""
    SELECT p.codigo, p.presi
    FROM legacy_proda p
    WHERE p.presi > 0
""")

# Atualiza Odoo
cur_odoo = odoo.cursor()
for codigo, presi in cur:
    cur_odoo.execute("""
        UPDATE product_template 
        SET standard_price = %s 
        WHERE default_code = %s
    """, (float(presi), codigo))

odoo.commit()
```

## Agendamento
- Linux: cron job diário ou a cada N horas
- Ou trigger pelo PDD após sync
