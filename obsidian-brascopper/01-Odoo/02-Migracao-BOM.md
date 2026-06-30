---
tags: [odoo, bom, mrp, migracao]
created: 2026-06-30
---

# Migração de BOMs

## Origem dos Dados
As BOMs (Bill of Materials) foram extraídas da tabela `erp_bom` no banco **nfehub** (localhost PostgreSQL). Esta tabela foi populada a partir do sistema legado Harbour (DBF) via `sync_legacydbf_raw`.

### Estrutura `erp_bom`
| Campo | Descrição |
|-------|-----------|
| `prod_px` | Prefixo do produto pai |
| `prod_co` | Código do produto pai |
| `comp_px` | Prefixo do componente |
| `comp_co` | Código do componente |
| `comp_sx` | Sufixo do componente |
| `quantidade` | Quantidade do componente |
| `unidade` | Unidade de medida |
| `sequencia` | Ordem na BOM |

## Script
`scripts/migracao/migrar_estrutura_manufatura.py`

### Fluxo
1. Lê `erp_bom` do nfehub
2. Cria `product.template` para cada produto técnico faltante (catálogo técnico)
3. Cria `product_product` para cada template
4. Cria `mrp_bom` para cada produto pai (product_tmpl_id)
5. Cria `mrp_bom_line` para cada componente

### Resultado
- **5.672 BOMs** criadas
- **27.809 linhas** de BOM
- Todas com `product_id = NULL` (vinculadas ao template, não à variante)

### Problemas Corrigidos
- `product_uom_id` estava ausente no INSERT original — adicionado
- `ready_to_produce` e `consumption` adicionados
- Savepoints para evitar falha em lote
- `active = NULL` corrigido para `true` após migração
- `picking_type_id = NULL` corrigido após migração

## BOMs no Odoo
- Acessar: Fabricação → Listas de Materiais (action 489)
- Para ver componentes de um produto: abrir a BOM e clicar em "Componentes"
- Cálculo de custo: botão "Calcular Custo" na BOM
