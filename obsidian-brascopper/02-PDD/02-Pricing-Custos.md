---
tags: [pdd, custos, pricing, margem]
created: 2026-06-30
---

# PDD — Pricing e Custos

## Módulo Precificação
App Django `precificacao` (80% completo) responsável por:
- Cálculo de margem sobre matéria-prima (AMM)
- Importação de preços de planilhas Excel
- Integração com SQL Server

## AMM — Análise de Margem sobre MP
Equivalente Django do relatório Harbour `amm/amm.prg`.

### Rota
`/precificacao/amm/` — GET (form) / POST (calcular)

### Fórmula
```
M% = (valor - impostos - mprim) / (valor - impostos) × 100
```

Onde:
- `valor = ittot + ivsub - itcus` (faturado - desconto + S.T.)
- `impostos` = IPI / ICMS / S.T. / PIS+COFINS
- `mprim` = custo MP = BOM × peso × `proda.presi`

### Fontes de Dados (DBF → PG)
| Tabela | Origem | Conteúdo |
|--------|--------|----------|
| findup | adm/findup.dbf | Cabeçalho NF |
| itfat | adm/itfat.dbf | Itens NF |
| itbb | adm/itbb.dbf | Descrição + peso (tb800) |
| tbpro | ind/tbpro.dbf | BOM componentes |
| proda | tab/proda.dbf | Preço atual MP (`presi`) |

### Cálculo de Peso (kg MP)
```python
if iteun == "Kg":
    quakg = (itqua / tb800) * peso_comp
else:
    quakg = peso_comp * (itqua / 1000.0)
mprim += presi * quakg
```

### Saída
3 tabelas ordenadas por faturamento:
1. Por Produto — código + descrição + valores + MP + M%
2. Por Cliente — nome + representante + totais + M%
3. Por Representante — nome + totais + M%

## Custo no Odoo
- `product_template.standard_price` = custo padrão
- BOM → "Calcular Custo" soma componentes × quantidade
- Pode incluir mão de obra (work centers) e custos indiretos

## Integração Proposta
PDD calcula `mprim` (custo MP) → atualiza `standard_price` no Odoo
Via:
1. API REST (PDD expõe endpoint, Odoo consome)
2. Script direto ao banco Odoo (UPDATE product_template SET standard_price)
3. Webhook do PDD para Odoo
