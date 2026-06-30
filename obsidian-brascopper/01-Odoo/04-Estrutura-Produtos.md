---
tags: [odoo, produtos, estrutura]
created: 2026-06-30
---

# Estrutura de Produtos

## Modelo de Dados Odoo

```
product.template (modelo)
  ├── id (PK)
  ├── default_code — Código do produto (ex: 001.005)
  ├── name — Nome/descrição (JSON)
  ├── type — product (estocável) | consu (consumível)
  ├── categ_id — Categoria
  ├── uom_id — Unidade de medida
  ├── list_price — Preço de venda
  ├── standard_price — Custo padrão
  └── active — Ativo
  
product.product (variante)
  ├── id (PK)
  ├── product_tmpl_id (FK → product.template)
  ├── default_code — Código da variante
  ├── combination_indices — Binário (atributos)
  └── active — Ativo
  
product.template.attribute.line
  ├── product_tmpl_id (FK)
  ├── attribute_id (FK → product.attribute)
  └── value_ids (M2M → product.attribute.value)

product.template.attribute.value
  ├── product_tmpl_id (FK)
  ├── attribute_line_id (FK)
  └── product_attribute_value_id (FK)
```

## Relação com BOMs

```
product.template (001.005)
  ├── mrp.bom (1)
  │   └── mrp.bom.line (N) → product_product (componente)
  └── product.product (N variantes)
      ├── 001.005 (original técnico)
      ├── 901.005.07
      ├── 901.005.09
      └── ...
```

## SQL Úteis
```sql
-- Buscar template por código
SELECT * FROM product_template WHERE default_code = '001.005';

-- Buscar variantes de um template
SELECT pp.id, pp.default_code, pp.active
FROM product_product pp
WHERE pp.product_tmpl_id = (SELECT id FROM product_template WHERE default_code = '001.005');

-- BOM com componentes
SELECT b.id, bl.product_id, bl.product_qty, pp.default_code
FROM mrp_bom b
JOIN mrp_bom_line bl ON bl.bom_id = b.id
JOIN product_product pp ON pp.id = bl.product_id
WHERE b.product_tmpl_id = (SELECT id FROM product_template WHERE default_code = '001.005');

-- Templates técnicos com variantes
SELECT pt.default_code, COUNT(pp.id) AS variantes
FROM product_template pt
JOIN product_product pp ON pp.product_tmpl_id = pt.id
WHERE pt.default_code ~ '^[0-9]{3}\.[0-9]{3}$'
GROUP BY pt.default_code
ORDER BY pt.default_code;
```
