---
tags: [odoo, variantes, atributos, migracao]
created: 2026-06-30
---

# Migração de Variantes

## Objetivo
Vincular produtos comerciais (código `XXX.XXX.XX`) como variantes de produtos técnicos (código `XXX.XXX`).

## Estrutura de Códigos
| Formato | Tipo | Exemplo |
|---------|------|---------|
| `000.000` | Template técnico | `001.005` — FIO COBRE NU 2,50 mm2 |
| `000.000.XX` | Variante comercial | `001.005.09` — FIO COBRE NU 2,50 mm2 AZUL |

## Atributo Criado
- **Atributo**: "Código Variante" (ID 2)
- **Tipo**: Custom
- **Valores**: 100 sufixos (`01` a `99`, `20` a `20`)

## Script
`scripts/migracao/migrar_para_variantes.py`

### Fluxo
1. Cria atributo "Código Variante" com valores de sufixo
2. Para cada template técnico com produtos comerciais vinculados:
   - Cria `product.template.attribute.line` (linha de atributo)
   - Cria `product.template.attribute.value` (valor do atributo)
   - Atualiza `product_product` do produto comercial:
     - `product_tmpl_id` → template técnico
     - `combination_indices` → binário do atributo
     - `product_template_attribute_value_id` → ptav criado

### Resultado
- **5.887 produtos comerciais** migrados como variantes
- **11.645 produtos** sob templates técnicos
- **65.141 produtos comerciais** restantes (sem vínculo técnico)
- **60.328 templates comerciais** desativados

### Problemas Resolvidos
- **13 registros** falharam por sufixo duplicado — produtos 9xx/9xx já ocuparam o sufixo nos templates técnicos
- **Resolução**: 13 produtos 0xx duplicados desativados (e seus templates comerciais órfãos)
- Comandos executados em 2026-06-30: `UPDATE product_product SET active=false` + `UPDATE product_template SET active=false`
- Os 13 produtos 9xx/9xx/9xx permanecem como variantes ativas sob os templates técnicos

## Produtos Técnicos Especiais
- `001.512`: "Sem nome" — produtos sem descrição no catálogo técnico
- Estes templates servem como fallback para produtos comerciais sem correspondência técnica clara

## Verificação
```sql
-- Ver produtos sob templates técnicos
SELECT pt.default_code, COUNT(pp.id) AS variantes
FROM product_template pt
JOIN product_product pp ON pp.product_tmpl_id = pt.id
WHERE pt.default_code ~ '^[0-9]{3}\.[0-9]{3}$'
GROUP BY pt.default_code;
```
