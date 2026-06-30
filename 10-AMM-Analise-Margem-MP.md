---
tags: [brascopper, django, precificacao, amm]
created: 2026-06-24
---

# AMM — Análise de Margem sobre Matéria Prima

Equivalente Django do relatório legado `amm/amm.prg` (Harbour/CGI).

## Rota

| URL | Nome | Método |
|-----|------|--------|
| `/precificacao/amm/` | `precificacao:amm_relatorio` | GET (form) / POST (calcular) |

Adicionado ao menu CUSTO em `core/views.py` e ao sidebar de `templates/painel/base.html`.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `precificacao/views_amm.py` | Lógica de cálculo completa |
| `precificacao/urls.py` | Rota `/amm/` |
| `templates/precificacao/amm_relatorio.html` | Template Bootstrap com 3 tabelas |

## Fórmula de margem

```
M% = (valor - impostos - mprim) / (valor - impostos) × 100
```

onde:
- `valor = ittot + ivsub - itcus` (faturado - desconto + S.T.)
- `impostos` = selecionáveis: IPI / ICMS / S.T. / PIS+COFINS (default: S.T.)
- `mprim` = custo de matéria-prima calculado pelo BOM × peso × `proda.presi`

## Fontes de dados (DBF via PostgreSQL espelho)

| Model | DBF | Campo-chave |
|-------|-----|-------------|
| `LegacyFindup` | `adm/findup.dbf` | Cabeçalho NF + data + RCOD |
| `LegacyItfat` | `adm/itfat.dbf` | Itens de NF |
| `LegacyItbb` | `adm/itbb.dbf` | Descrição + `tb800` (g/m total) |
| `LegacyTbpro` | `ind/tbpro.dbf` | BOM — componentes por produto |
| `LegacyProda` | `tab/proda.dbf` | Preço atual MP (`presi`) |
| `LegacyRepre` | `adm/repre.dbf` | Nome do representante |
| `LegacyClient` | `adm/client.dbf` | Nome do cliente |

## Filtros aplicados (equivalentes ao legado)

- `findup.fator = "1"` — apenas NFs normais (não devoluções)
- `findup.rcod NOT IN ("100","101","991","992")` — exclui representantes intragrupo/internos
- `itfat.it_px NOT LIKE "9%"` — exclui devoluções
- `itfat.it_px NOT LIKE "3%"` — exclui telefonia
- `rcod = "092"` (MOBRA) — excluído do cálculo de margem

## Cálculo de peso (kg MP)

```python
if iteun == "Kg":
    quakg = (itqua / tb800) * peso_comp   # vendido em Kg
else:
    quakg = peso_comp * (itqua / 1000.0)  # vendido em metros
mprim += presi * quakg
```

## Saída

Três tabelas ordenadas por faturamento DESC:
1. **Por Produto** — código + descrição + metros/kg/valor/impostos/MP/M%
2. **Por Cliente** — nome + representante + totais + M%
3. **Por Representante** — nome + totais + M%

Painel de resumo (cards): NFs, Metros, Kg MP, Fat.Bruto, Impostos, R$ MP  
Alerta colorido com M% total (verde ≥30%, amarelo ≥15%, vermelho <15%)  
Aviso de produtos sem BOM (mprim = 0)

## Relação com PDD

O AMM usa `findup.fdata` (data de saída). O PDD usa `emissao`. Divergências de período entre os dois relatórios são normais para NFs emitidas no final do mês.

Golden Flex SP (12697) e ES (12698) estão excluídos por `rcod IN (RCOD_EXCLUIR)` — são intragrupo com `tipo_emp=3`.
