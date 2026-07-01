#!/bin/bash
set -e

echo "============================================"
echo "Sync Completo de Custos - $(date)"
echo "============================================"

# 1. Cotações de metais + dólar
echo ""
echo ">>> 1/6 Cotações de Mercado"
python3 /opt/nfelazarus/scripts/agentes/cotacoes_commodities.py
echo ""

# 2. Preços de matérias-primas do legado (PVC, XLPE, EPR, etc → legacy_proda)
echo ""
echo ">>> 2/6 Preços de Matérias-Primas (Legado)"
python3 /opt/nfelazarus/scripts/agentes/sync_legacy_prices.py
echo ""

# 3. Precifica semi-acabados (cordas, fios, veias de cobre/aço/alumínio)
echo ""
echo ">>> 3/6 Precificação de Semi-Acabados"
python3 /opt/nfelazarus/scripts/agentes/precificar_semi_acabados.py
echo ""

# 4. Sincroniza dados do PDD (se Windows estiver acessível)
echo ">>> 4/6 Sync PDD (via comando remoto, se disponível)"
echo "  (opcional - rodar manualmente no Windows: py manage.py sync_all)"
echo ""

# 5. Preços de notas de compra (COMCIT → standard_price)
echo ">>> 5/6 Preços de Notas de Compra"
python3 /opt/nfelazarus/scripts/agentes/extrair_precos_compras.py
echo ""

# 6. Recalcula custos no Odoo
echo ">>> 6/6 Atualizando Custos no Odoo"
python3 /opt/nfelazarus/scripts/migracao/sync_custos_odoo.py
echo ""

echo "============================================"
echo "Concluído em $(date)"
echo "============================================"
