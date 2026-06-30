#!/bin/bash
set -e

echo "============================================"
echo "Sync Completo de Custos - $(date)"
echo "============================================"

# 1. Cotações de metais + dólar
echo ""
echo ">>> 1/4 Cotações de Mercado"
python3 /opt/nfelazarus/scripts/agentes/cotacoes_commodities.py
echo ""

# 2. Sincroniza dados do PDD (se Windows estiver acessível)
echo ">>> 2/4 Sync PDD (via comando remoto, se disponível)"
echo "  (opcional - rodar manualmente no Windows: py manage.py sync_all)"
echo ""

# 3. Preços de notas de compra (COMCIT → standard_price)
echo ">>> 3/4 Preços de Notas de Compra"
python3 /opt/nfelazarus/scripts/agentes/extrair_precos_compras.py
echo ""

# 4. Recalcula custos no Odoo
echo ">>> 4/4 Atualizando Custos no Odoo"
python3 /opt/nfelazarus/scripts/migracao/sync_custos_odoo.py
echo ""

echo "============================================"
echo "Concluído em $(date)"
echo "============================================"
