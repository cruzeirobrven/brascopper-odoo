#!/usr/bin/env python3
"""
Migra estrutura de manufatura para Odoo 18:
1. Catalogo tecnico (proda.dbf) → product.template
2. BOM (compo.dbf) → mrp.bom + mrp.bom.line

Uso: python3 migrar_estrutura_manufatura.py
"""
import sys, json, time, math
from decimal import Decimal
from pathlib import Path
from collections import defaultdict
import psycopg2
from psycopg2.extras import execute_values

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
BATCH = 5000

def esc(val):
    if val is None:
        return 'NULL'
    return "'" + str(val).replace("'", "''") + "'"
def criar_templates_tecnicos():
    """Cria product.template para produtos do catalogo tecnico que estao no BOM"""
    print("=== 1. Criando templates tecnicos ===")

    # Connect directly to avoid RealDictCursor issues
    pg_local = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')
    conn_local = psycopg2.connect(**pg_local)
    cur_local = conn_local.cursor()
    
    cur_local.execute("""
        WITH bom_codes AS (
            SELECT DISTINCT prod_px, prod_co FROM erp_bom
            UNION
            SELECT DISTINCT comp_px, comp_co FROM erp_bom
        )
        SELECT DISTINCT
            b.prod_px || '.' || b.prod_co AS codigo,
            COALESCE(NULLIF(TRIM(cat.descricao), ''), 'Sem nome') AS nome,
            CASE WHEN cat.ptipo IS NULL OR cat.ptipo = '' OR cat.ptipo IN ('199','116','299','399','140','230','240')
                 THEN 'product' ELSE 'consu' END AS tipo,
            COALESCE(cat.peso_kg, 0) AS peso_kg,
            cat.ptipo,
            cat.unidade,
            CASE WHEN b2.codigo IS NOT NULL THEN true ELSE false END AS tem_como_componente
        FROM bom_codes b
        LEFT JOIN erp_catalogo_tecnico cat ON cat.pi_px = b.prod_px AND cat.pi_co = b.prod_co
        LEFT JOIN (SELECT DISTINCT comp_px || '.' || comp_co AS codigo FROM erp_bom) b2
            ON b2.codigo = b.prod_px || '.' || b.prod_co
        ORDER BY codigo
    """)
    cols = [d[0] for d in cur_local.description]
    rows = [dict(zip(cols, row)) for row in cur_local.fetchall()]
    conn_local.close()

    total = len(rows)
    products = [r for r in rows if r['tipo'] == 'product']
    consumables = [r for r in rows if r['tipo'] == 'consu']
    print(f"  Total: {total} (product: {len(products)}, consu: {len(consumables)})")

    conn = psycopg2.connect(**ODOO_PG)
    cur = conn.cursor()

    # Filter out existing templates
    existing = set()
    cur.execute("SELECT default_code FROM product_template WHERE default_code IS NOT NULL")
    for r in cur.fetchall():
        existing.add(r[0])

    novos = [r for r in rows if r['codigo'] not in existing]
    print(f"  Ja existem: {total - len(novos)}, Novos: {len(novos)}")

    if not novos:
        conn.close()
        return

    t0 = time.time()
    created = 0
    for r in novos:
        name_json = json.dumps({'en_US': r['nome']})
        try:
            cur.execute("""
                INSERT INTO product_template (
                    name, default_code, type, categ_id,
                    uom_id, uom_po_id, list_price, weight,
                    active, sale_ok, purchase_ok,
                    service_tracking, sale_line_warn, tracking,
                    create_uid, create_date, write_uid, write_date
                ) VALUES (
                    %s, %s, %s, 1,
                    1, 1, 0, %s,
                    true, true, true,
                    'no', 'no', 'none',
                    2, NOW(), 2, NOW()
                )
            """, (name_json, r['codigo'], r['tipo'], float(r['peso_kg'])))
            created += 1

            if created % 1000 == 0:
                conn.commit()
                elapsed = time.time() - t0
                print(f"    {created}/{len(novos)} templates ({elapsed:.0f}s)")

        except Exception as e:
            print(f"    ERRO ao criar {r['codigo']}: {e}")

    conn.commit()
    elapsed = time.time() - t0
    print(f"  Criados {created} templates em {elapsed:.0f}s")

    # Create product_product for each new template
    print("  Criando product_product...")
    codes_list = tuple(r['codigo'] for r in novos)
    if codes_list:
        # Create a temp table approach instead of VALUES
        cur.execute("CREATE TEMP TABLE tmp_codes (codigo VARCHAR(10)) ON COMMIT DROP")
        from psycopg2.extras import execute_values
        execute_values(cur, "INSERT INTO tmp_codes (codigo) VALUES %s", [(c,) for c in codes_list], page_size=1000)
        cur.execute("""
            INSERT INTO product_product (product_tmpl_id, default_code, active, create_uid, create_date, write_uid, write_date)
            SELECT pt.id, pt.default_code, true, 2, NOW(), 2, NOW()
            FROM product_template pt
            JOIN tmp_codes tc ON tc.codigo = pt.default_code
            WHERE NOT EXISTS (
                SELECT 1 FROM product_product pp WHERE pp.product_tmpl_id = pt.id
            )
        """)
        conn.commit()

    cur.close()
    conn.close()
    print(f"  Feito! ({time.time()-t0:.0f}s)")


def criar_boms():
    """Cria mrp.bom + mrp.bom.line para todos os produtos do BOM"""
    print("\n=== 2. Criando BOMs ===")

    pg_local = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')
    conn_local = psycopg2.connect(**pg_local)
    cur_local = conn_local.cursor()
    
    cur_local.execute("""
        SELECT
            b.prod_px || '.' || b.prod_co AS prod_codigo,
            b.comp_px || '.' || b.comp_co || '.' || COALESCE(b.comp_sx, '00') AS comp_codigo_full,
            b.comp_px || '.' || b.comp_co AS comp_codigo,
            b.quantidade,
            b.unidade,
            CAST(b.sequencia AS INTEGER) AS sequencia,
            c.descricao AS prod_nome,
            cc.descricao AS comp_nome
        FROM erp_bom b
        LEFT JOIN erp_catalogo_tecnico c ON c.pi_px = b.prod_px AND c.pi_co = b.prod_co
        LEFT JOIN erp_catalogo_tecnico cc ON cc.pi_px = b.comp_px AND cc.pi_co = b.comp_co
        WHERE b.quantidade > 0
        ORDER BY prod_codigo, sequencia
    """)
    cols = [d[0] for d in cur_local.description]
    rows = [dict(zip(cols, row)) for row in cur_local.fetchall()]
    conn_local.close()

    print(f"  Total BOM lines: {len(rows)}")

    conn = psycopg2.connect(**ODOO_PG)
    cur = conn.cursor()

    # Get template ID mapping
    cur.execute("SELECT id, default_code FROM product_template WHERE default_code IS NOT NULL")
    tmpl_map = {r[1]: r[0] for r in cur.fetchall()}

    # Group by product
    boms = defaultdict(list)
    for r in rows:
        boms[r['prod_codigo']].append(r)

    t0 = time.time()
    bom_count = 0
    line_count = 0
    skipped = 0

    for prod_code, lines in boms.items():
        tmpl_id = tmpl_map.get(prod_code)
        if not tmpl_id:
            skipped += 1
            continue

        # Use savepoint so a single BOM failure doesn't abort the whole transaction
        cur.execute("SAVEPOINT bom_sp")

        try:
            # Get uom_id from template
            cur.execute("SELECT uom_id FROM product_template WHERE id = %s", (tmpl_id,))
            uom_row = cur.fetchone()
            uom_id = uom_row[0] if uom_row else 1

            cur.execute("""
                INSERT INTO mrp_bom (
                    product_tmpl_id, product_qty, product_uom_id,
                    ready_to_produce, consumption,
                    type, sequence,
                    company_id, create_uid, create_date, write_uid, write_date
                ) VALUES (%s, 1.0, %s,
                    'all_available', 'strict',
                    'normal', 1, 1, 2, NOW(), 2, NOW())
                RETURNING id
            """, (tmpl_id, uom_id))
            bom_id = cur.fetchone()[0]
            bom_count += 1

            # Create BOM lines
            for line in lines:
                comp_tmpl_id = tmpl_map.get(line['comp_codigo'])
                if not comp_tmpl_id:
                    continue

                # Get product_product for component
                cur.execute("""
                    SELECT id FROM product_product
                    WHERE product_tmpl_id = %s
                    LIMIT 1
                """, (comp_tmpl_id,))
                pp_row = cur.fetchone()
                if not pp_row:
                    continue

                cur.execute("""
                    INSERT INTO mrp_bom_line (
                        bom_id, product_id, product_qty, product_uom_id, sequence,
                        company_id, create_uid, create_date, write_uid, write_date
                    ) VALUES (%s, %s, %s, %s, %s, 1, 2, NOW(), 2, NOW())
                """, (bom_id, pp_row[0], float(line['quantidade']), uom_id, line['sequencia'] or 1))
                line_count += 1

            cur.execute("RELEASE SAVEPOINT bom_sp")

            if bom_count % 500 == 0:
                conn.commit()
                elapsed = time.time() - t0
                print(f"    {bom_count} BOMs, {line_count} linhas ({elapsed:.0f}s)")

        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT bom_sp")
            print(f"    ERRO BOM {prod_code}: {e}")

    conn.commit()
    elapsed = time.time() - t0
    print(f"  Criados {bom_count} BOMs, {line_count} linhas ({elapsed:.0f}s)")
    if skipped:
        print(f"  Pulados {skipped} produtos sem template")

    cur.close()
    conn.close()


if __name__ == '__main__':
    criar_templates_tecnicos()
    criar_boms()
