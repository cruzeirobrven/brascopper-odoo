---
tags: [roteiro, variantes, executado]
created: 2026-06-30
---

# Roteiro — Migração de Variantes

## Data
2026-06-30

## Script
`/opt/nfelazarus/scripts/migracao/migrar_para_variantes.py`

## Objetivo
Transformar produtos comerciais (`XXX.XXX.XX`) em variantes de produtos técnicos (`XXX.XXX`).

## Pré-requisitos
1. Catálogo técnico importado (PRODA → product.template)
2. Produtos comerciais importados (ESTPRO → product.template + product.product)
3. Mapeamento IT_PX/IT_CO ↔ código técnico (tabela `erp_produto_tecnico_mapping`)

## Passos Executados

### 1. Criar Atributo "Código Variante"
```sql
INSERT INTO product_attribute (name, create_uid, create_date, write_uid, write_date)
VALUES ('{"en_US": "Codigo Variante"}', 2, NOW(), 2, NOW());
-- ID = 2
```

### 2. Criar Valores do Atributo (01 a 99, 20)
100 valores criados na tabela `product_attribute_value` com atributo_id = 2.

### 3. Vincular Produtos
Para cada template técnico com produtos comerciais:
1. Criar `product_template_attribute_line`
2. Criar `product_template_attribute_value` (ptav)
3. Atualizar `product_product`:
   - `product_tmpl_id` → template técnico
   - `combination_indices` → binário do atributo
   - `product_template_attribute_value_id` → ptav

### 4. Desativar Templates Comerciais
```sql
UPDATE product_template SET active = false 
WHERE default_code ~ '^[0-9]{3}\.[0-9]{3}\.';
```

## Resultados
- **5.887 produtos** migrados como variantes
- **11.645 produtos** sob templates técnicos
- **65.141 produtos** restantes (comerciais sem técnico)
- **60.328 templates** desativados

## Problemas
- **13 erros** por sufixo duplicado (IT_SX repetido)
- Produtos migrados ficaram `active = false` (corrigir se necessário)
- Busca no Odoo pode não encontrar por default_code do template

## Verificação
```bash
PGPASSWORD=MULETA psql -U postgres -h 100.119.223.92 -d odoo18 -c "
SELECT pt.default_code, COUNT(pp.id) AS variantes
FROM product_template pt
JOIN product_product pp ON pp.product_tmpl_id = pt.id
WHERE pt.default_code ~ '^[0-9]{3}\.[0-9]{3}$'
  AND pt.active = true
GROUP BY pt.default_code
ORDER BY pt.default_code;
"
```
