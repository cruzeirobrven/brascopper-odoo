#!/bin/bash
# Migra BOM (compo.dbf) e catalogo tecnico (proda.dbf) para Odoo 18
# Passo 1: Criar product.template tecnicos
# Passo 2: Criar mrp.bom + mrp.bom.line
#
# Uso: ./migrar_bom_odoo.sh

set -e
ODOO_PG="host=100.119.223.92 user=postgres password=MULETA dbname=odoo18"

echo "=== PASSO 1: Identificando produtos do BOM que precisam de template tecnico ==="

# Export matching data from local PG
PGPASSWORD=nfehub123 psql -U nfehub -h localhost -d nfehub -At -c "
COPY (
    -- Finished products from BOM that are in proda (technical catalog)
    SELECT DISTINCT
        c.pi_px || '.' || c.pi_co AS codigo,
        COALESCE(NULLIF(TRIM(c.descricao), ''), 'Sem nome') AS nome,
        'product' AS tipo,
        COALESCE(c.peso_kg, 0) AS peso_kg
    FROM erp_bom b
    JOIN erp_catalogo_tecnico c ON c.pi_px = b.prod_px AND c.pi_co = b.prod_co
) TO STDOUT WITH CSV;
" > /tmp/prod_bom_tec.csv

echo "Exportados $(wc -l < /tmp/prod_bom_tec.csv) produtos tecnicos do BOM"

# Also export raw materials from BOM (components)
PGPASSWORD=nfehub123 psql -U nfehub -h localhost -d nfehub -At -c "
COPY (
    SELECT DISTINCT
        c.pi_px || '.' || c.pi_co AS codigo,
        COALESCE(NULLIF(TRIM(c.descricao), ''), 'Sem nome') AS nome,
        CASE WHEN c.ptipo IS NULL OR c.ptipo = '' OR c.ptipo IN ('199','116','299','399') THEN 'product' ELSE 'consu' END AS tipo,
        COALESCE(c.peso_kg, 0) AS peso_kg
    FROM erp_bom b
    JOIN erp_catalogo_tecnico c ON c.pi_px = b.comp_px AND c.pi_co = b.comp_co
) TO STDOUT WITH CSV;
" > /tmp/prod_comp_tec.csv

echo "Exportados $(wc -l < /tmp/prod_comp_tec.csv) componentes do BOM"

echo ""
echo "=== PASSO 2: Criando templates tecnicos no Odoo ==="

PGPASSWORD=MULETA psql -U postgres -h 100.119.223.92 -d odoo18 << 'SQL'
-- Create temp table for technical products
CREATE TABLE tmp_prod_tec (
    codigo VARCHAR(10),
    nome VARCHAR(200),
    tipo VARCHAR(10),
    peso_kg NUMERIC
);

\copy tmp_prod_tec FROM '/tmp/prod_bom_tec.csv' WITH CSV

-- Insert only NEW products (not already in product_template by default_code)
INSERT INTO product_template (
    name, default_code, type, categ_id,
    uom_id, uom_po_id, list_price, weight,
    active, sale_ok, purchase_ok,
    service_tracking, sale_line_warn, tracking,
    create_uid, create_date, write_uid, write_date
)
SELECT
    jsonb_build_object('en_US', t.nome),
    t.codigo,
    t.tipo,
    1,  -- All category (will update later based on ESTGRP mapping)
    1, 1, 0, t.peso_kg,
    true, true, true,
    'no', 'no', 'none',
    2, NOW(), 2, NOW()
FROM tmp_prod_tec t
WHERE NOT EXISTS (
    SELECT 1 FROM product_template pt
    WHERE pt.default_code = t.codigo
);

-- Also create product_product for each new template
INSERT INTO product_product (product_tmpl_id, default_code, active, barcode, create_uid, create_date, write_uid, write_date)
SELECT pt.id, pt.default_code, true, NULL, 2, NOW(), 2, NOW()
FROM product_template pt
WHERE pt.default_code IN (SELECT codigo FROM tmp_prod_tec)
  AND NOT EXISTS (
    SELECT 1 FROM product_product pp WHERE pp.product_tmpl_id = pt.id
  );

DROP TABLE tmp_prod_tec;

-- Count results
SELECT COUNT(*) AS total_templates_tecnicos FROM product_template
WHERE default_code IN (SELECT codigo FROM (
    SELECT DISTINCT c.pi_px || '.' || c.pi_co AS codigo FROM erp_bom b
    JOIN erp_catalogo_tecnico c ON c.pi_px = b.prod_px AND c.pi_co = b.prod_co
) x);
SQL

echo ""
echo "=== Feito! ==="
