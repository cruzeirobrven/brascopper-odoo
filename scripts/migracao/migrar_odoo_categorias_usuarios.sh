#!/bin/bash
# Migra ESTGRP → product.category e USUGRP/USUCAD → res.groups/res.users no Odoo 18
# Uso: ./migrar_odoo_categorias_usuarios.sh

set -e

ODOO_PG="host=100.119.223.92 user=postgres password=MULETA dbname=odoo18"

echo "=== 1. Migrando ESTGRP → product.category ==="

PSQL_ODOO="psql \"$ODOO_PG\" -At"

# Limpa categorias criadas pelo nfe_hub (opcional, comentado)
# $PSQL_ODOO -c "DELETE FROM product_category WHERE name LIKE '[nfe_hub]%' AND parent_id IS NULL;"

# Cria categorias nivel 1
$PSQL_ODOO << 'SQL'
-- Level 1: "00" e "01"
INSERT INTO product_category (name, parent_id, create_date, write_date)
SELECT
    CASE g.n1
        WHEN '00' THEN '[nfe_hub] 00 - Fios e Cabos de Cobre'
        WHEN '01' THEN '[nfe_hub] 01 - Cabos Especiais'
        ELSE '[nfe_hub] ' || g.n1
    END,
    NULL,
    NOW(), NOW()
FROM (SELECT DISTINCT LEFT(grupo, 2) AS n1 FROM erp_grupos_produtos) g
WHERE NOT EXISTS (
    SELECT 1 FROM product_category pc
    WHERE pc.name LIKE '[nfe_hub]%' || g.n1 || '%' AND pc.parent_id IS NULL
)
ON CONFLICT DO NOTHING;
SQL

# Cria categorias nivel 2 (AA.BBB)
$PSQL_ODOO << 'SQL'
INSERT INTO product_category (name, parent_id, create_date, write_date)
SELECT DISTINCT
    '[nfe_hub] ' || LEFT(g.grupo, 6) || ' - ' || g.descricao,
    pc.id,
    NOW(), NOW()
FROM erp_grupos_produtos g
JOIN product_category pc ON pc.name LIKE '[nfe_hub]' || LEFT(g.grupo, 2) || '%' AND pc.parent_id IS NULL
WHERE NOT EXISTS (
    SELECT 1 FROM product_category pc2
    WHERE pc2.name LIKE '[nfe_hub] ' || LEFT(g.grupo, 6) || '%'
)
LIMIT 5;
SQL

echo "  Categorias migradas."

echo ""
echo "=== 2. Atualizando product_template.categ_id ==="
echo "  (pula por enquanto - precisa mapear grupo do erp_produtos para product_category)"

echo ""
echo "=== 3. Migrando USUGRP → res.groups ==="
$PSQL_ODOO << 'SQL'
INSERT INTO res_groups (name, comment, create_date, write_date)
SELECT
    g.descricao,
    '[nfe_hub] Grupo ERP: ' || g.grupo,
    NOW(), NOW()
FROM erp_grupos_usuarios g
WHERE g.grupo NOT IN ('SISTEMA')  -- skip system group
AND NOT EXISTS (
    SELECT 1 FROM res_groups rg WHERE rg.name = g.descricao
);
SQL

echo ""
echo "=== 4. Migrando USUCAD → res.users ==="
echo "  (pula - requer senha hasheada e configuracao segura)"

echo ""
echo "=== Pronto! ==="
