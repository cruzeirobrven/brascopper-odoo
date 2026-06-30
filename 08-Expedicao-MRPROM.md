---
tags: [brascopper, expedicao, mrprom, romaneio]
created: 2026-06-08
---

# Módulo Expedição — Pedidos de Venda + Romaneios MRP

## Estrutura de tabelas ERP (SQL Server)

```
VENPED (pedido de venda / OSC)
└── VENITN — itens do pedido

MRPEXP (expedição MRP — cabeçalho, vincula ao VENPED via OSC)
└── MRPEX1 — lista de produtos a expedir (qtde teórica / faltante)
    └── MRPROM (romaneio — agrupa volumes de uma expedição)
        └── MRPRO1 — volumes e itens (árvore: PARENTE=0=volume, PARENTE>0=item)
            └── MRPR1D — sub-itens agrupados dentro de um item
```

## Script SQL de criação

`D:\BRASC\PRG\sqlserver\CREATE_MRPROM_TABLES.sql`

- Todos os `CREATE TABLE` têm guarda `IF NOT EXISTS`
- Inclui `INSERT INTO AUTOREG` para MRPEXP e MRPROM
- Inclui `ALTER TABLE VENPED ADD CONSIGNATARIO NUMERIC(9,0)` se não existir
- Inclui índices: `IX_MRPEX1_PRODUTO`, `IX_MRPROM_MRPEXP`, `IX_MRPROM_OSC`, `IX_MRPRO1_PARENTE`, `IX_TMPROM_MAQUINA`

## MRPRO1 — Lógica da árvore

| PARENTE | PRODUTO | Significado |
|---------|---------|-------------|
| 0 | NULL | Cabeçalho de volume (dimensões, peso, embalagem) |
| N | código | Item dentro do volume N (filho do item cujo ITEM=N com PARENTE=0) |

Sequências internas:
- `ITEM` = `MAX(ITEM)+1 WHERE REGISTRO=...` por romaneio
- `VOLUME` = `MAX(VOLUME)+1 WHERE REGISTRO=... AND PRODUTO IS NULL`
- `SUB_ITEM` = `MAX(SUB_ITEM)+1 WHERE REGISTRO=... AND ITEM=...` (em MRPR1D)

## TMPROM — Seleção temporária por estação

Tabela `TMPROM` limpa com `DELETE WHERE MAQUINA=...` ao abrir/fechar o formulário Delphi. Não tem FK — nunca deve ser importada para PDD (dado volátil).

## Models Django (PostgreSQL espelho)

| Model | Tabela PG | Tabela ERP |
|-------|----------|-----------|
| `ErpPedidoVenda` | `expedicao_erp_pedido_venda` | VENPED |
| `ErpItemPedidoVenda` | `expedicao_erp_item_pedido_venda` | VENITN |
| `ErpExpedicaoMrp` | `expedicao_mrp_exp` | MRPEXP |
| `ErpItemExpedicaoMrp` | `expedicao_mrp_ex1` | MRPEX1 |
| `ErpRomaneioMrp` | `expedicao_mrp_rom` | MRPROM |
| `ErpRomaneioItem` | `expedicao_mrp_ro1` | MRPRO1 |
| `ErpRomaneioSubItem` | `expedicao_mrp_r1d` | MRPR1D |

## Importação

```powershell
# Pedidos e itens de venda
py manage.py import_sqlserver_expedicao --table all

# Romaneios MRP (MRPEXP / MRPEX1 / MRPROM / MRPRO1 / MRPR1D)
py manage.py import_sqlserver_romaneio --table all

# Tabelas individuais
py manage.py import_sqlserver_romaneio --table exp   # só MRPEXP
py manage.py import_sqlserver_romaneio --table rom   # só MRPROM
py manage.py import_sqlserver_romaneio --table ro1   # só MRPRO1
```

## URLs

| URL | View | Descrição |
|-----|------|-----------|
| `/expedicao/` | `index` | Dashboard: stats pedidos + romaneios MRP |
| `/expedicao/pedidos/` | `pedidos` | Lista pedidos de venda com filtros |
| `/expedicao/pedidos/<reg>/` | `pedido_detalhe` | Detalhe do pedido com itens |
| `/expedicao/expedicoes-mrp/` | `expedicoes_mrp` | Lista MRPEXP |
| `/expedicao/expedicoes-mrp/<reg>/` | `expedicao_mrp_detalhe` | Detalhe com MRPEX1 e romaneios vinculados |
| `/expedicao/romaneios-mrp/` | `romaneios_mrp` | Lista MRPROM |
| `/expedicao/romaneios-mrp/<reg>/` | `romaneio_mrp_detalhe` | Detalhe com volumes/itens (árvore MRPRO1) |
| `/expedicao/romaneios-expedir/` | `romaneios_expedir` | Romaneios legado Harbour |

## Reconciliação Harbour ↔ VENPED

URL: `/expedicao/reconciliacao/`  
View: `reconciliacao_pedidos`

Mostra quais pedidos do Harbour (pedido.dbf) já foram sincronizados para o SQL Server VENPED.

**Modos:**
- `?modo=pendentes` — pedidos do Harbour que ainda não estão no VENPED (padrão)
- `?modo=sincronizados` — pedidos já presentes em ambos
- `?modo=todos` — todos os pedidos Harbour

**Lógica de comparação:**
```python
venped_numeros = set(ErpPedidoVenda.objects.values_list('pedido', flat=True))
no_venped = int(pv.numero) in venped_numeros
```

**Stats no dashboard (`/expedicao/`):**
- Harbour (DBF): total de `PedidoVenda.objects.count()`
- VENPED (SQL): total de `ErpPedidoVenda.objects.count()`
- Botão "Pendentes de sync" → `reconciliacao?modo=pendentes`

Para sincronizar, usar `push_harbour_to_venped` — ver [[09-Sync-Rotinas]].

---

## URLs completas

| URL | View | Descrição |
|-----|------|-----------|
| `/expedicao/` | `index` | Dashboard: stats pedidos + romaneios MRP |
| `/expedicao/pedidos/` | `pedidos` | Lista pedidos de venda com filtros |
| `/expedicao/pedidos/<reg>/` | `pedido_detalhe` | Detalhe do pedido com itens |
| `/expedicao/expedicoes-mrp/` | `expedicoes_mrp` | Lista MRPEXP |
| `/expedicao/expedicoes-mrp/<reg>/` | `expedicao_mrp_detalhe` | Detalhe com MRPEX1 e romaneios vinculados |
| `/expedicao/romaneios-mrp/` | `romaneios_mrp` | Lista MRPROM |
| `/expedicao/romaneios-mrp/<reg>/` | `romaneio_mrp_detalhe` | Detalhe com volumes/itens (árvore MRPRO1) |
| `/expedicao/romaneios-expedir/` | `romaneios_expedir` | Romaneios legado Harbour |
| `/expedicao/reconciliacao/` | `reconciliacao_pedidos` | Harbour ↔ VENPED: pendentes de sync |

## ErpItemPedidoVenda.total_linha

Propriedade calculada: `quantidade × valor`. Usada no template `pedido_detalhe.html` coluna "Total" por item.
