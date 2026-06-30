---
tags: [banco, sqlserver, erp]
created: 2026-06-30
---

# Banco — SQL Server ERP Brascopper

## Conexão
- Server: `DESKTOP-M2UK50B\SQL2022`
- Database: `BRVEN_BRASCOPPER`
- User: `sa`
- Instância: Windows (100.98.13.77)
- Acesso PDD: via pyodbc (settings.SQLSERVER_ERP)

## Tabelas Relevantes

### Produtos
| Tabela | Conteúdo |
|--------|----------|
| ESTPRO | Produtos (estoque + comercial) |
| PRODA | Catálogo técnico (matéria-prima) |
| IT_PX | Prefixos de produto |
| IT_CO | Códigos de produto |

### Vendas
| Tabela | Conteúdo |
|--------|----------|
| VENPED | Pedidos de venda |
| VENITN | Itens do pedido |
| MRPEXP | Expedições |
| MRPROM | Romaneios |

### Compras
| Tabela | Conteúdo |
|--------|----------|
| COMPED | Pedidos de compra |
| COMITC | Itens de compra |
| COMNOT | Notas fiscais de entrada |
| COMCIT | Itens da NF de entrada |

### Financeiro
| Tabela | Conteúdo |
|--------|----------|
| PAGDUP | Duplicatas a pagar |
| PAGPAG | Pagamentos |
| RECDUP | Duplicatas a receber |
| RECREC | Recebimentos |

## Acesso via PDD
```python
c = settings.SQLSERVER_ERP
cn = pyodbc.connect(
    f"DRIVER={{{c['driver']}}};"
    f"SERVER={c['server']};"
    f"DATABASE={c['database']};"
    f"UID={c['user']};"
    f"PWD={c['password']}"
)
```

## Observações
- ~1.450 tabelas no banco
- Dados são fonte primária — PDD e Odoo são leitores
- Atualizações são feitas pelo ERP Delphi
- PDD sincroniza via `sync_all` a cada 5 minutos
