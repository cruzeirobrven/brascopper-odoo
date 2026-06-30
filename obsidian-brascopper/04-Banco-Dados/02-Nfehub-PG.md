---
tags: [banco, nfehub, postgresql, pdd]
created: 2026-06-30
---

# Banco — Nfehub PostgreSQL

## Conexão
- Host: 100.119.223.92 (Linux) / localhost (Windows)
- Porta: 5432
- Database: `nfehub`
- User: `nfehub`
- Password: `nfehub123`

## Tabelas de Interesse

### Catálogo Técnico
| Tabela | Conteúdo |
|--------|----------|
| `erp_catalogo_tecnico` | Catálogo técnico de produtos (PRODA) |
| `erp_produto_tecnico_mapping` | Mapeamento IT_PX/IT_CO ←→ código técnico |
| `erp_bom` | BOM técnica (componentes) |

### Legado (DBF → PG)
| Tabela | DBF Origem | Conteúdo |
|--------|-----------|----------|
| `legacy_proda` | tab/proda.dbf | Preços de matéria-prima |
| `legacy_tbpro` | ind/tbpro.dbf | BOM componentes |
| `legacy_findup` | adm/findup.dbf | Faturamento (cabeçalho) |
| `legacy_itfat` | adm/itfat.dbf | Itens de fatura |
| `legacy_itbb` | adm/itbb.dbf | Descrição + peso |
| `legacy_repre` | adm/repre.dbf | Representantes |
| `legacy_client` | adm/client.dbf | Clientes |
| `legacy_estpro` | tab/estpro.dbf | Produtos comerciais ERP |

### ERP Espelho
| Tabela | SQL Server | Conteúdo |
|--------|-----------|----------|
| `import_VENPED` | VENPED | Pedidos de venda |
| `import_MRPROM` | MRPROM | Romaneios |
| `import_CADCLI` | CADCLI | Clientes |
| `import_CADFOR` | CADFOR | Fornecedores |
| `import_COMNOT` | COMNOT | Notas fiscais entrada |

## Consultas Úteis
```sql
-- Preço MP de um produto
SELECT codigo, presi, data_ativ FROM legacy_proda WHERE codigo = '296.019';

-- BOM de um produto
SELECT * FROM erp_bom WHERE prod_px || '.' || prod_co = '001.005' ORDER BY sequencia;

-- Mapeamento IT_PX → código técnico
SELECT * FROM erp_produto_tecnico_mapping WHERE it_px = '001' AND it_co = '005';
```
