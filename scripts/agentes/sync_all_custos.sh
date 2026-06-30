#!/bin/bash
set -e

echo "============================================"
echo "Sync Completo de Custos - $(date)"
echo "============================================"

# 1. Cotações de metais + dólar
echo ""
echo ">>> 1/5 Cotações de Mercado"
python3 /opt/nfelazarus/scripts/agentes/cotacoes_commodities.py
echo ""

# 2. Preços de matérias-primas do legado (PVC, XLPE, EPR, etc → legacy_proda)
echo ">>> 2/5 Preços de Matérias-Primas (Legado)"
python3 /opt/nfelazarus/scripts/agentes/sync_legacy_prices.py
echo ""

# 3. Sincroniza dados do PDD (se Windows estiver acessível)
echo ">>> 3/5 Sync PDD (via comando remoto, se disponível)"
echo "  (opcional - rodar manualmente no Windows: py manage.py sync_all)"
echo ""

# 4. Preços de notas de compra (COMCIT → standard_price)
echo ">>> 4/5 Preços de Notas de Compra"
python3 /opt/nfelazarus/scripts/agentes/extrair_precos_compras.py
echo ""

# 5. Recalcula custos no Odoo
echo ">>> 5/5 Atualizando Custos no Odoo"
python3 /opt/nfelazarus/scripts/migracao/sync_custos_odoo.py
echo ""

echo "============================================"
echo "Concluído em $(date)"
echo "============================================"
