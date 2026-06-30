---
tags: [agentes, precos, historico, rastreabilidade]
created: 2026-06-30
---

# Histórico de Preços Aplicados

## Formato
O histórico de preços é registrado em `/opt/nfelazarus/logs/historico_precos.jsonl` (JSON Lines — um JSON por linha).

## Campos
| Campo | Descrição |
|-------|-----------|
| `ts` | Timestamp ISO |
| `fonte` | Origem: `commodities`, `commodities_legacy_proda`, `compra_comcit`, `bom_calculo` |
| `produto` | Código do produto (commodity code, ERP code, etc.) |
| `nome` | Nome do produto (quando disponível) |
| `preco` | Valor aplicado |
| `detalhe` | Informação adicional (fonte da cotação, etc.) |

## Pipeline

```
cotacoes_commodities.py
  ├── commodities → prec_commodity_price_period (COBRE, ALUMINIO)
  └── commodities_legacy_proda → legacy_proda.presi (999.101, 999.102, 999.518-532)

extrair_precos_compras.py
  └── compra_comcit → product_product.standard_price (646 produtos)

sync_custos_odoo.py
  └── bom_calculo → product_product.standard_price (5.499 templates)
```

## Estado Atual (2026-06-30)
- **5.499 templates** com custo calculado via BOM
- **173 templates** ainda sem preço (componentes sem custo)
- **646 produtos** precificados via notas de compra (COMCIT)
- **6 produtos** precificados via commodities (cobre, alumínio)

## Comandos de Consulta
```bash
# Últimos 10 registros
tail -10 /opt/nfelazarus/logs/historico_precos.jsonl

# Contar por fonte
jq -r '.fonte' /opt/nfelazarus/logs/historico_precos.jsonl | sort | uniq -c

# Preços de um produto específico
grep '"999.101"' /opt/nfelazarus/logs/historico_precos.jsonl | jq .
```
