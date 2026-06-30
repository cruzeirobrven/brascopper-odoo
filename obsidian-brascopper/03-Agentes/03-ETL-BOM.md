---
tags: [agente, etl, bom, producao]
created: 2026-06-30
---

# Agente — ETL de BOMs

## Origem
Tabela `erp_bom` no banco nfehub (espelho do Harbour `ind/tbpro.dbf`).

## Destino
`mrp_bom` + `mrp_bom_line` no banco odoo18.

## Mapeamento

### erp_bom → mrp_bom
| erp_bom | mrp_bom | Observação |
|---------|---------|------------|
| prod_px + prod_co | product_tmpl_id | JOIN product_template.default_code |
| — | product_qty | Sempre 1.0 (qtd por lote) |
| — | type | 'normal' |
| — | ready_to_produce | 'all_available' |
| — | consumption | 'strict' |

### erp_bom → mrp_bom_line
| erp_bom | mrp_bom_line | Observação |
|---------|-------------|------------|
| comp_px + comp_co | product_id | JOIN product_template → product_product |
| quantidade | product_qty | Quantidade do componente |
| sequencia | sequence | Ordem na BOM |

## Script
`scripts/migracao/migrar_estrutura_manufatura.py`

## Execução
```bash
python3 /opt/nfelazarus/scripts/migracao/migrar_estrutura_manufatura.py
```

## Manutenção Futura
Quando novas BOMs forem cadastradas no ERP, o sync deve:
1. Comparar `erp_bom` com `mrp_bom` existentes
2. Criar novas BOMs
3. Atualizar linhas existentes
4. Desativar BOMs obsoletas

## SQL de Verificação
```sql
-- Contar BOMs e linhas
SELECT COUNT(*) AS boms FROM mrp_bom;
SELECT COUNT(*) AS linhas FROM mrp_bom_line;

-- BOMs sem linhas
SELECT b.id, pt.default_code
FROM mrp_bom b
JOIN product_template pt ON pt.id = b.product_tmpl_id
WHERE NOT EXISTS (SELECT 1 FROM mrp_bom_line bl WHERE bl.bom_id = b.id);
```
