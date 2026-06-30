# Agentes de Custo — Brascopper

Pipeline automatizada de custos: cotações → banco → Odoo.

## Scripts

| Script | Função |
|--------|--------|
| `cotacoes_commodities.py` | Busca cobre, alumínio, dólar via APIs gratuitas |
| `sync_custos_odoo.py` | Calcula custo BOM e atualiza Odoo |
| `sync_all_custos.sh` | Orquestrador completo |

## Uso

```bash
# Tudo de uma vez
bash /opt/nfelazarus/scripts/agentes/sync_all_custos.sh

# Só cotações
python3 /opt/nfelazarus/scripts/agentes/cotacoes_commodities.py

# Só custos
python3 /opt/nfelazarus/scripts/migracao/sync_custos_odoo.py
```

## Agendamento (cron)

Automático diariamente às 06:00:
```cron
0 6 * * * /opt/nfelazarus/scripts/agentes/sync_all_custos.sh >> /opt/nfelazarus/logs/sync_custos.log 2>&1
```

## APIs utilizadas
- AwesomeAPI (USD/BRL) — gratuita, sem chave
- TradingEconomics / GitHub (cobre) — dados públicos

## Próximos passos
- Extrair preços de notas de compra (`prec_sqlserver_com*`)
- Integrar cotação do alumínio via API dedicada
- Preços de energia elétrica
