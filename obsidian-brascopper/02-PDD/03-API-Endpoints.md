---
tags: [pdd, api, endpoints]
created: 2026-06-30
---

# PDD — API Endpoints

## Endpoints Existentes
Base: `http://100.119.223.92:8800` (ou `http://100.98.13.77:8800`)

| URL | App | Descrição |
|-----|-----|-----------|
| `/` | core | Home / Painel |
| `/precificacao/amm/` | precificacao | Relatório AMM (form+POST) |
| `/suprimentos/` | suprimentos | Pedidos de compra |
| `/recebimentos/` | recebimentos | Recebimentos NF |
| `/financeiro/` | financeiro | Contas a pagar/receber |
| `/cadastros/` | cadastros | Clientes, fornecedores |
| `/custos/` | custos | Análise de custos |

## Endpoints Propostos para Integração Odoo

### GET /api/precos/{codigo_produto}
Retorna o custo calculado para um produto:
```json
{
  "codigo": "001.005",
  "custo_mp": 1.2345,
  "data_calculo": "2026-06-30",
  "fonte": "proda.presi",
  "bom": true
}
```

### POST /api/odoo/sync-custos
Dispara sincronização em lote dos custos para Odoo:
```json
{
  "atualizados": 1523,
  "erros": 0,
  "timestamp": "2026-06-30T14:00:00Z"
}
```

### POST /api/odoo/webhook
Recebe notificações do Odoo (ex: produto criado, BOM alterada):
```json
{
  "evento": "product.created",
  "model": "product.template",
  "id": 172520,
  "default_code": "001.005"
}
```
