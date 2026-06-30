# Manufatura Brascopper — Estrutura e Migração para Odoo

## Visão Geral

Brascopper CBC fabrica fios e cabos de cobre. O processo produtivo é:

```
MP (matéria prima) → OF (ordem de fabricação) → Máquinas/Operações → Produto Acabado → Expedição
```

Dados de manufatura residem em:
1. **DBF/Harbour** (`D:\BRASC\dad\`) — sistema legado atual
2. **SQL Server** (`brven_brascopper`) — mirror parcial via MSSQL
3. **PostgreSQL PDD** (`brascopper_pdd`) — Django com import dos DBFs via `sync_*` commands
4. **Nosso PostgreSQL** (`nfehub`) — schema `erp_*` importado do SQL Server
5. **Odoo 18** (`odoo18`) — destino da migração

## Tags
#manufatura #brascopper #odoo #migracao #bom #producao

---

## 1. Fontes de Dados de Manufatura

### 1.1 SQL Server (brven_brascopper)

Tabelas já importadas para `nfehub` com prefixo `erp_`:

| Tabela | Registros | Conteúdo |
|--------|-----------|----------|
| `erp_produtos` (ESTPRO) | 68.763 | Todos os produtos (acabados + insumos) |
| `erp_grupos_produtos` (ESTGRP) | 283 | Grupos com hierarquia `AA.BBB.CCC` |
| `erp_clientes` (CADCLI) | 12.425 | Clientes |
| `erp_notas` (FATNOT) | 33.313 | Notas fiscais |
| `erp_itens_nota` (FATITN) | 67.196 | Itens de notas |
| `erp_operacoes` (FATOPE) | 193 | Operações fiscais |

**NÃO estão no SQL Server** as tabelas de engenharia/produção (BOM, roteiro, OF, máquinas). Elas só existem em DBF.

### 1.2 DBF → Django PDD

O projeto Django em `PRG/06082025/pdd/` já importou os DBFs para PostgreSQL. Comandos de sync:

```bash
python manage.py sync_compo_dbf          # BOM (compo.dbf → BomCaboLegacy)
python manage.py sync_vlmpr_dbf          # Preços MP (vlmpr.dbf → PrecoMaterialLegacy)
python manage.py calcular_custo_mp       # Explosão multi-nível de custos
python manage.py sync_legacydbf_raw --models LegacyCemrp LegacyOscem LegacyOsigr LegacyRearm LegacyRepit
```

### 1.3 DBFs Relevantes (D:\BRASC\dad\)

#### Cadastro de Produtos
| DBF | Registros | Descrição |
|-----|-----------|-----------|
| `tab\proda.dbf` | ~8.141 | Catálogo unificado (acabados + MP) |
| `tab\prodt.dbf` | — | Ficha técnica (liga IT_GR.IT_BI → PI_PX.PI_CO) |
| `tab\tbpro.dbf` | — | Parâmetros técnicos (tbcod=800 = peso base g/m) |

#### BOM (Bill of Materials)
| DBF | Registros | Descrição |
|-----|-----------|-----------|
| `tab\compo.dbf` | 27.833 | **Principal BOM**: produto → componente + quantidade |
| `tab\compp.dbf` | — | BOM por grupo/bitola (alternativa) |

#### Preços de Matéria Prima
| DBF | Registros | Descrição |
|-----|-----------|-----------|
| `tab\vlmpr.dbf` | 28.294 | Preços mensais R$/kg (208 materiais, 89 ativos) |

#### Produção (Ordens e Operações)
| DBF | Registros | Descrição |
|-----|-----------|-----------|
| `adm\oscem.dbf` | 61 | Ordens de Fabricação (status: AB/AP/FE/CA/RE) |
| `alu\osigr.dbf` | ~80K | Apontamento por máquina |
| `alu\cemrp.dbf` | ~14K | Liberações de produção |
| `adm\rearm.dbf` | ~19.4K | Operações de rearme (setup/produção) |
| `alu\repit.dbf` | ~25.4K | Bobinas M.I. (material intermediário) |
| `ind\maqui.dbf` | 315 | Cadastro de máquinas |
| `ind\fases.dbf` | — | Fases industriais |
| `ind\maqpd.dbf` | — | Capacidade diária por máquina |

---

## 2. Estrutura do BOM (compo.dbf → BomCaboLegacy)

### Schema do BomCaboLegacy (Django)

```python
class BomCaboLegacy(models.Model):
    id = models.AutoField(primary_key=True)
    prod_px = models.CharField(max_length=3)     # PI_PX do produto acabado
    prod_co = models.CharField(max_length=3)     # PI_CO do produto acabado
    prod_descr = models.CharField()              # Descrição do produto
    comp_px = models.CharField(max_length=3)     # MP_PX do componente
    comp_co = models.CharField(max_length=3)     # MP_CO do componente
    comp_sx = models.CharField(max_length=3)     # MP_SX do componente
    comp_descr = models.CharField()              # Descrição do componente
    comp_tipo = models.CharField()               # 'MP' ou 'EM' (matéria prima / embalagem)
    comp_cat = models.CharField()                # Categoria do componente
    sequencia = models.IntegerField()            # Ordem na BOM
    quantidade = models.DecimalField()           # Quantidade do componente
    unidade = models.CharField()                 # Unidade
    peso_unit_kg = models.DecimalField()         # Peso unitário (g/m)
```

### Registros: 27.833 (~100% coverage)
### Produtos distintos com BOM: 5.673

### Estrutura Multi-nível

A explosão de BOM revela até 6 níveis:

```
Nível 0: 89 materiais base (matéria prima pura, ex: cobre, PVC)
Nível 1: +1.992 semi-acabados
Nível 2: +487
Nível 3: +150
Nível 4: +13
Nível 5: +2
Total:   2.733 produtos com custo calculado
```

### Cadeia de lookup:

```
ItemTecnicoFamilia(it_px, it_co) 
  → FichaTecnicaProduto(it_gr, it_bi) 
    → pi_px, pi_co 
      → BomCaboLegacy(prod_px, prod_co)
```

89.2% das famílias têm FichaTecnicaProduto
51.0% das famílias têm BOM via chain (1.484/2.912)

---

## 3. Estrutura de Produtos (proda.dbf)

### Chave primária composta
`PI_PX.PI_CO` — namespace único para acabados E insumos.

Exemplo:
- `001.006` = produto acabado (fio cobre)
- `999.101` = cobre (matéria prima)
- `999.010` = PVC (matéria prima)

### Campos principais
- `prokg` = peso técnico (kg/m)
- `presi` = custo unitário (para análise de margem AMM)

### Diferenciação: acabado vs insumo
No namespace unificado, a diferenciação pode ser feita por:
1. Se aparece em `vlmpr.dbf` → matéria prima
2. Campo `ptipo` no proda (verificar)
3. Se tem BOM como `prod_px.prod_co` → produto acabado/semi-acabado

---

## 4. Preços de Matéria Prima (vlmpr.dbf → PrecoMaterialLegacy)

### Schema
```python
class PrecoMaterialLegacy(models.Model):
    pi_px = models.CharField(max_length=3)
    pi_co = models.CharField(max_length=3)
    anome = models.CharField(max_length=6)    # AAAAMM
    preco = models.DecimalField()             # R$/kg
```

### Registros: 28.294 (208 materiais, 89 com preços ativos)

### Preços chave (Maio/2026):
| Material | Código | Preço (R$/kg) |
|----------|--------|---------------|
| Cobre | 999.101 | ~80,00 |
| PVC | 999.010 | ~7,40 |

---

## 5. Mapeamento Odoo

### 5.1 Produtos

| Origem | Odoo | Observação |
|--------|------|------------|
| `ESTPRO.PRODUTO` | `product_template.default_code` | Código ERP |
| `ESTPRO.DESCRICAO` | `product_template.name` | Nome |
| `proda.prokg` | `product_template.weight` | Peso técnico (kg/m) |
| `ESTPRO.GRUPO` → `ESTGRP` | `product_template.categ_id` | Categoria (já migrada) |
| `ESTPRO.VENDA` | `product_template.list_price` | Preço de venda |
| `ESTPRO.EAN_PRODUTO` | `product_product.barcode` | Código de barras |
| Se tem BOM em `compo.dbf` | `type = 'product'` (fabricado) | Diferenciar de insumo |
| Se NÃO tem BOM | `type = 'consu'` (consumível/MP) | Insumo ou produto acabado simples |

### 5.2 BOM (Bill of Materials)

| Origem | Odoo | Observação |
|--------|------|------------|
| `compo.dbf` | `mrp.bom` | BOM principal |
| `compo.dbf.MPQUA` | `mrp.bom.line.product_qty` | Quantidade |
| `compo.dbf.MPUNI` | `uom_id` | Unidade de medida |
| `compo.dbf.MPQRE` | `mrp.bom.line.sequence` | Sequência |
| Diferenciação MP/EM | `mrp.bom.line.type` | 'normal' ou 'pack' |

### 5.3 Centro de Trabalho (Work Center)

| Origem | Odoo |
|--------|------|
| `maqui.dbf` (315 máquinas) | `mrp.workcenter` |
| `maqpd.dbf` | `mrp.workcenter.capacity` (capacidade) |
| `fases.dbf` | `mrp.routing.workcenter` (roteiro) |

### 5.4 Ordens de Fabricação

| Origem | Odoo |
|--------|------|
| `oscem.dbf` | `mrp.production` |
| `osigr.dbf` | `mrp.workorder` (apontamento) |
| Status AB=confirmado/AP=em_producao/FE=done/CA=cancel | `mrp.production.state` |

### 5.5 Roteiro (Routing)

| Origem | Odoo |
|--------|------|
| Sequência de operações por produto | `mrp.routing` + `mrp.workcenter` |
| `rearm.dbf` (setup/produção) | Tempos de setup e produção |

---

## 6. Estratégia de Migração

### Fase 1: Produtos ✅ (Concluída)
- [x] Importar `ESTPRO` → PostgreSQL `erp_produtos`
- [x] Importar `ESTGRP` → PostgreSQL `erp_grupos_produtos`
- [x] Sincronizar `erp_produtos` → Odoo `product.template` (via `upsert_product()`)
- [x] Sincronizar categorias (ESTGRP → `product_category`)
- [x] Atualizar `categ_id` nos produtos

### Fase 2: BOM ✅ (Dados importados, pendente Odoo)
- [x] Acessar `compo.dbf` via SMB da máquina ACBrMonitor (100.98.13.77)
- [x] Criar tabela `erp_bom` no PostgreSQL local (27.833 registros)
- [x] Importar `compo.dbf` para `erp_bom`
- [x] Importar `proda.dbf` → `erp_catalogo_tecnico` (8.141 registros)
- [x] Importar `vlmpr.dbf` → `erp_precos_mp` (28.294 registros de preços)
- [ ] Criar PL/pgSQL `upsert_bom()` no Odoo
- [ ] Diferenciar produtos fabricados (`type='product'`) de insumos (`type='consu'`)
- [ ] Atualizar `product_template.type` conforme BOM
- [ ] Criar BOMs no Odoo (`mrp.bom` + `mrp.bom.line`)

### Fase 3: Matéria Prima 🔲
- [x] Importar `proda.dbf` (catálogo unificado, 8.141 produtos técnicos)
- [x] Importar `vlmpr.dbf` (28.294 preços históricos)
- [ ] Identificar MPs no catálogo técnico: PTIPO vazio/simples = insumo, PTIPO 199/116/299/399 = acabado
- [ ] Criar produtos tipo `consu` para MPs que não existem
- [ ] Vincular preços ao Odoo (`product.supplierinfo` ou `product.price_history`)

### Fase 4: Produção 🔲 (Futuro)
- [ ] Importar `maqui.dbf` → Odoo `mrp.workcenter`
- [ ] Importar `fases.dbf` + `maqpd.dbf` → Odoo `mrp.routing`
- [ ] Importar `oscem.dbf` → Odoo `mrp.production`
- [ ] Importar `osigr.dbf` + `rearm.dbf` → Odoo `mrp.workorder`

---

## 7. Observações Técnicas

### Chave Primária dos Produtos
- `proda.dbf`: `PI_PX.PI_CO` (ex: `001.006`, `999.101`)
- `ESTPRO`: `PRODUTO` (ex: `001.006.20`)
- `erp_produtos.codigo_erp`: texto livre (ex: `001.006.20`)
- **Relação**: `PI_PX.PI_CO` = primeiros 3 caracteres + '.' + próximos 3 = `PRODUTO` sem o sufixo

Exemplo:
- `PRODUTO` = `001.006.20` → `PI_PX` = `001`, `PI_CO` = `006` (ignora `.20`)

### Namespace Compartilhado
`proda.dbf` usa **mesmo namespace** para acabados e MPs:
- Acabados: `001.000` a `100.999`
- MPs: `999.000` a `999.999`
- Cobre: `999.101`, PVC: `999.010`

### Dependência de Dados
- BOM precisa de produtos existentes (já migrados)
- Roteiro precisa de work centers
- OF precisa de BOM + produtos + work centers

### Categorias
Hierarquia ESTGRP: `AA.BBB.CCC` (já migrada para `product_category`)
- `00` = Fios e Cabos de Cobre (183 grupos)
- `01` = Materiais e Suprimentos (100 grupos)
