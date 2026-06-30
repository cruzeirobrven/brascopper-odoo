---
tags: [banco, odoo, postgresql]
created: 2026-06-30
---

# Banco — Odoo PostgreSQL

## Conexão
- Host: 100.119.223.92
- Porta: 5432
- Database: `odoo18`
- User: `postgres`
- Password: `MULETA`

## Tabelas Principais

### Produtos
| Tabela | Conteúdo |
|--------|----------|
| `product_template` | Modelos de produto (código técnico) |
| `product_product` | Variantes de produto |
| `product_attribute` | Atributos (ex: Código Variante) |
| `product_attribute_value` | Valores de atributo (ex: 01, 02...) |
| `product_template_attribute_line` | Linha de atributo por template |
| `product_template_attribute_value` | ptav (template + valor) |
| `product_pricelist` | Tabelas de preço |
| `product_pricelist_item` | Itens de tabela de preço |
| `product_category` | Categorias |
| `product_supplierinfo` | Informações de fornecedor |
| `product_uom` | Unidades de medida |

### BOM / MRP
| Tabela | Conteúdo |
|--------|----------|
| `mrp_bom` | Listas de materiais |
| `mrp_bom_line` | Componentes da BOM |
| `mrp_routing` | Roteiros de fabricação |
| `mrp_workcenter` | Centros de trabalho |
| `mrp_production` | Ordens de produção |
| `stock_picking_type` | Tipos de operação |

### Vendas / Compras
| Tabela | Conteúdo |
|--------|----------|
| `sale_order` | Pedidos de venda |
| `sale_order_line` | Itens do pedido |
| `purchase_order` | Pedidos de compra |
| `purchase_order_line` | Itens de compra |
| `stock_move` | Movimentações de estoque |
| `stock_valuation_layer` | Camadas de valuation |

## Consultas Úteis
```sql
-- Produtos técnicos com BOM
SELECT pt.default_code, pt.name
FROM product_template pt
WHERE EXISTS (SELECT 1 FROM mrp_bom b WHERE b.product_tmpl_id = pt.id);

-- Templates com mais variantes
SELECT pt.default_code, COUNT(pp.id) AS vars
FROM product_template pt
JOIN product_product pp ON pp.product_tmpl_id = pt.id
GROUP BY pt.default_code
HAVING COUNT(pp.id) > 1
ORDER BY COUNT(pp.id) DESC;
```
