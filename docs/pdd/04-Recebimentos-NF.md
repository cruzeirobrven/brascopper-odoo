---
tags: [brascopper, recebimentos, nf-entrada]
created: 2026-06-07
---

# Módulo Recebimentos — NF de Entrada

## Estrutura de tabelas ERP

```
COMNOT (cabeçalho da NF)
├── COMCIT  — itens produto aplicação direta     (12.429 registros)
├── COMEIT  — itens produto para estoque         (2 registros)
├── COMNSE  — itens de serviço                  (3.786 registros)
└── COMNFI  — parcelas financeiras               (10.242 registros)
```

### Vínculos com Pedidos de Compra

- **Cabeçalho:** `COMNOT.REG_PEDIDO = COMPED.REGISTRO`
- **Itens:** `COMCIT.PEDIDO = COMPED.PEDIDO` e `COMCIT.ITEM_PEDIDO = COMITC.ITEM`

## Models Django (PostgreSQL espelho)

| Model | Tabela SQL | Tabela ERP |
|-------|-----------|-----------|
| `ErpNotaFiscalEntrada` | `recebimentos_erp_nf_entrada` | COMNOT |
| `ErpItemNFDireto` | `recebimentos_erp_item_nf_direto` | COMCIT |
| `ErpItemNFEstoque` | `recebimentos_erp_item_nf_estoque` | COMEIT |
| `ErpItemNFEntrada` | `recebimentos_erp_item_nf` | COMNSE |
| `ErpParcelaNFEntrada` | `recebimentos_erp_parcela_nf` | COMNFI |

## Importação

```powershell
py manage.py import_sqlserver_recebimentos --table all
# ou individual:
py manage.py import_sqlserver_recebimentos --table notas
py manage.py import_sqlserver_recebimentos --table itens_direto
```

## URLs

| URL | View | Descrição |
|-----|------|-----------|
| `/recebimentos/` | `index` | Dashboard stats |
| `/recebimentos/nfe-produtos/` | `notas_fiscais` | Lista com filtros |
| `/recebimentos/nfe-produtos/<reg>/` | `nota_fiscal_detalhe` | Detalhe com itens e parcelas |
| `/recebimentos/entrada-produtos-servicos/` | `entrada_produtos_servicos` | Resumo por período |
| `/recebimentos/xml-nfe/` | `xml_dashboard` | Painel de importação XML |

## Nota sobre `it.nf_itens` e `it.pc_registro`

O template `nota_fiscal_detalhe.html` usa atributos anotados em tempo de execução:
- `it.pc_registro` — REGISTRO do COMPED, calculado via `pedido_reg_map` no view
- `it.nf_itens` — lista de itens NF para o item do PC, em `pedido_compra_detalhe`

Isso evita usar `get_item` filter (não existe em Django templates).
