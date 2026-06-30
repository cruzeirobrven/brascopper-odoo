---
tags: [roteiro, bom, executado]
created: 2026-06-30
---

# Roteiro — Criação de BOMs

## Data
2026-06-30

## Script
`/opt/nfelazarus/scripts/migracao/migrar_estrutura_manufatura.py`

## Passos Executados

### 1. Criar Templates Técnicos
```bash
python3 migrar_estrutura_manufatura.py
```
- Criou `product.template` para produtos do catálogo técnico
- Criou `product_product` correspondente

### 2. Criar BOMs
- Leu `erp_bom` do nfehub
- Agrupou por produto pai
- Criou `mrp_bom` (1 por template)
- Criou `mrp_bom_line` (N por BOM)

### 3. Correções Pós-Migração
```sql
UPDATE mrp_bom SET active = true WHERE active IS NULL;
UPDATE mrp_bom SET picking_type_id = (
    SELECT id FROM stock_picking_type WHERE code = 'mrp_operation' LIMIT 1
) WHERE picking_type_id IS NULL;
```

## Resultados
- **5.672 BOMs** criadas
- **27.809 linhas** de BOM
- Todas ativas e com tipo de operação configurado

## Problemas Enfrentados
1. `product_uom_id` ausente no INSERT → adicionado
2. `ready_to_produce` e `consumption` ausentes → adicionados
3. `active = NULL` → corrigido para `true`
4. `picking_type_id = NULL` → configurado
