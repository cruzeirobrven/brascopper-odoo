#!/usr/bin/env python3
"""
Migra produtos comerciais para variantes dos templates tecnicos no Odoo 18.

Usa IT_SX (sufixo do codigo ERP, ex: .01, .20) como identificador de variante.

Uso: python3 migrar_para_variantes.py [--dry-run]
"""
import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import psycopg2
from psycopg2.extras import execute_values

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
PG_LOCAL = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')
DRY_RUN = '--dry-run' in sys.argv


def criar_atributo_variante(cur):
    """Cria atributo 'Codigo Variante' (sufixo ERP)"""
    cur.execute("SELECT id FROM product_attribute WHERE name->>'en_US' = 'Codigo Variante'")
    row = cur.fetchone()
    if row:
        attr_id = row[0]
        print(f"  Atributo 'Codigo Variante' ja existe (id={attr_id})")
    else:
        cur.execute("""
            INSERT INTO product_attribute (name, create_variant, display_type, sequence, active, create_uid, create_date, write_uid, write_date)
            VALUES (%s, 'no_variant', 'select', 1, true, 2, NOW(), 2, NOW())
            RETURNING id
        """, (json.dumps({'en_US': 'Codigo Variante'}),))
        attr_id = cur.fetchone()[0]
        print(f"  Atributo 'Codigo Variante' criado (id={attr_id})")

    # Get distinct IT_SX from mapping (via local nfehub)
    pg_local = psycopg2.connect(**PG_LOCAL)
    cur_local = pg_local.cursor()
    cur_local.execute("""
        SELECT DISTINCT m.it_sx
        FROM erp_produto_tecnico_mapping m
        JOIN erp_produtos e ON e.codigo_erp = m.codigo_erp
        WHERE m.it_sx IS NOT NULL AND TRIM(m.it_sx) != ''
          AND e.ativo = true
        ORDER BY m.it_sx
    """)
    suffixes = [r[0] for r in cur_local.fetchall() if r[0]]
    pg_local.close()
    print(f"  Sufixos (IT_SX) distintos: {len(suffixes)}")

    # Get existing attribute values
    cur.execute("""
        SELECT id, name->>'en_US' AS nome FROM product_attribute_value
        WHERE attribute_id = %s
    """, (attr_id,))
    existing = {r[1]: r[0] for r in cur.fetchall()}

    # Create new attribute values
    value_ids = {}
    t0 = time.time()
    created = 0
    seq = 1
    for sx in suffixes:
        key = sx.strip()
        if key in existing:
            value_ids[key] = existing[key]
        else:
            cur.execute("""
                INSERT INTO product_attribute_value (name, attribute_id, sequence, active, create_uid, create_date, write_uid, write_date)
                VALUES (%s, %s, %s, true, 2, NOW(), 2, NOW())
                RETURNING id
            """, (json.dumps({'en_US': key}), attr_id, seq))
            vid = cur.fetchone()[0]
            value_ids[key] = vid
            created += 1
        seq += 1

    print(f"  Criados {created} novos valores de variante")
    return attr_id, value_ids


def criar_attribute_lines(cur, attr_id, value_ids):
    """Cria product_template_attribute_line + values para cada template tecnico"""
    # Get mapping of product codes to technical templates and IT_SX
    pg_local = psycopg2.connect(**PG_LOCAL)
    cur_local = pg_local.cursor()
    cur_local.execute("""
        SELECT m.codigo_erp, m.it_sx,
               LPAD(COALESCE(NULLIF(TRIM(m.it_px), ''), '0'), 3, '0') || '.' ||
               LPAD(COALESCE(NULLIF(TRIM(m.it_co), ''), '0'), 3, '0') AS codigo_tecnico
        FROM erp_produto_tecnico_mapping m
        WHERE m.it_px IS NOT NULL AND m.it_co IS NOT NULL
          AND TRIM(m.it_px) != '' AND TRIM(m.it_co) != ''
          AND m.it_sx IS NOT NULL AND TRIM(m.it_sx) != ''
    """)
    mapping = {r[0]: (r[1].strip(), r[2]) for r in cur_local.fetchall()}
    pg_local.close()

    # Also get prefix-based mapping for products without IT_PX/IT_CO
    pg_local2 = psycopg2.connect(**PG_LOCAL)
    cur_local2 = pg_local2.cursor()
    cur_local2.execute("""
        SELECT codigo_erp, SUBSTRING(codigo_erp FROM 9 FOR 2) AS it_sx_fallback
        FROM erp_produtos
        WHERE codigo_erp ~ '^[0-9]{3}\.[0-9]{3}\.[0-9]+$'
    """)
    for r in cur_local2.fetchall():
        if r[0] not in mapping and r[1]:
            # Extract suffix: everything after the second dot
            sx = r[0].split('.')[2] if '.' in r[0] else ''
            tech_code = r[0][:7]
            mapping[r[0]] = (sx, tech_code)
    pg_local2.close()

    # Get all commercial products with technical link in Odoo
    cur.execute("""
        SELECT pt.id AS tmpl_id, pt.default_code, tt.id AS tech_tmpl_id
        FROM product_template pt
        JOIN product_template tt ON tt.default_code = pt.technical_default_code
        WHERE pt.technical_default_code IS NOT NULL
    """)
    products = {}
    for r in cur.fetchall():
        products[r[1]] = {'tmpl_id': r[0], 'tech_tmpl_id': r[2]}

    # Group products by technical template
    from collections import defaultdict
    template_groups = defaultdict(list)
    for prod_code, info in products.items():
        sx, tech_code = mapping.get(prod_code, (None, None))
        if not tech_code or tech_code not in {t: 1 for t in [info['tech_tmpl_id']]}:
            # Fallback: use default_code prefix
            if len(prod_code) >= 7:
                tech_code = prod_code[:7]
                sx = prod_code[8:] if len(prod_code) > 7 else None
        if sx:
            sx_clean = sx.strip()
            sx_key = sx_clean if sx_clean in value_ids or sx_clean == '' else None
            if sx_key:
                template_groups[info['tech_tmpl_id']].append({
                    'prod_code': prod_code,
                    'sx': sx_key,
                    'commercial_tmpl_id': info['tmpl_id'],
                })

    # Actually, let me do this differently. Get the raw data from Odoo
    # and match with mapping
    
    # Drop the in-memory data, query from Odoo directly
    cur.execute("""
        SELECT pt.id AS commercial_tmpl_id, pt.default_code,
               tt.id AS tech_tmpl_id,
               COALESCE(pt.technical_default_code, LEFT(pt.default_code, 7)) AS tech_code,
               SUBSTRING(pt.default_code FROM '\.([0-9]+)$') AS cod_sx
        FROM product_template pt
        JOIN product_template tt ON tt.default_code = pt.technical_default_code
        WHERE pt.technical_default_code IS NOT NULL
          AND pt.default_code ~ '\.[0-9]+$'
        ORDER BY tt.id
    """)
    rows = cur.fetchall()
    print(f"  Produtos comerciais com technical_default_code: {len(rows)}")

    # Group by technical template
    tg = defaultdict(list)
    for r in rows:
        tg[r[2]].append(r)

    t0 = time.time()
    line_count = 0
    ptav_count = 0
    ptav_map = {}

    for tech_tmpl_id, prods in tg.items():
        # Create attribute line if not exists
        cur.execute("""
            SELECT id FROM product_template_attribute_line
            WHERE product_tmpl_id = %s AND attribute_id = %s
        """, (tech_tmpl_id, attr_id))
        existing_line = cur.fetchone()
        if existing_line:
            attr_line_id = existing_line[0]
        else:
            cur.execute("""
                INSERT INTO product_template_attribute_line (product_tmpl_id, attribute_id, sequence, active, create_uid, create_date, write_uid, write_date)
                VALUES (%s, %s, 1, true, 2, NOW(), 2, NOW())
                RETURNING id
            """, (tech_tmpl_id, attr_id))
            attr_line_id = cur.fetchone()[0]
            line_count += 1

        for r in prods:
            commercial_tmpl_id, codigo, _, _, cod_sx = r
            if not cod_sx:
                continue
            sx_clean = cod_sx.strip()
            val_id = value_ids.get(sx_clean)
            if not val_id:
                continue

            # Create PTAV if not exists
            cur.execute("""
                SELECT id FROM product_template_attribute_value
                WHERE product_tmpl_id = %s AND attribute_line_id = %s
                  AND product_attribute_value_id = %s
            """, (tech_tmpl_id, attr_line_id, val_id))
            ptav_row = cur.fetchone()
            if ptav_row:
                ptav_id = ptav_row[0]
            else:
                cur.execute("""
                    INSERT INTO product_template_attribute_value (product_tmpl_id, attribute_line_id, attribute_id, product_attribute_value_id, ptav_active, create_uid, create_date, write_uid, write_date)
                    VALUES (%s, %s, %s, %s, true, 2, NOW(), 2, NOW())
                    RETURNING id
                """, (tech_tmpl_id, attr_line_id, attr_id, val_id))
                ptav_id = cur.fetchone()[0]
                ptav_count += 1

            ptav_map[(commercial_tmpl_id, val_id)] = ptav_id

        if line_count % 200 == 0:
            print(f"    {line_count} linhas, {ptav_count} ptavs ({time.time()-t0:.0f}s)")

    print(f"  Criadas {line_count} attribute_lines, {ptav_count} ptavs")
    return ptav_map


def migrar_product_products(conn, cur, value_ids, ptav_map):
    """Migra product.product para serem variantes dos templates tecnicos"""
    cur.execute("""
        SELECT pp.id AS pp_id, pt.id AS commercial_tmpl_id,
               tt.id AS new_tmpl_id,
               pt.default_code,
               SUBSTRING(pt.default_code FROM '\.([0-9]+)$') AS cod_sx
        FROM product_product pp
        JOIN product_template pt ON pp.product_tmpl_id = pt.id
        JOIN product_template tt ON tt.default_code = pt.technical_default_code
        WHERE pt.technical_default_code IS NOT NULL
          AND pt.default_code ~ '\.[0-9]+$'
    """)
    rows = cur.fetchall()
    print(f"  Product.products para migrar: {len(rows)}")

    # Get product_products already under technical templates
    cur.execute("""
        SELECT pp.id FROM product_product pp
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE pt.default_code ~ '^[0-9]{3}\.[0-9]{3}$'
    """)
    existing_under_tech = {r[0] for r in cur.fetchall()}

    # Set combination_indices for existing tech products (avoid '' conflicts)
    cur.execute("""
        UPDATE product_product pp SET combination_indices = 'base_' || pp.id::text
        FROM product_template pt
        WHERE pt.id = pp.product_tmpl_id
          AND pt.default_code ~ '^[0-9]{3}\.[0-9]{3}$'
          AND (pp.combination_indices IS NULL OR pp.combination_indices = '')
    """)
    updated_base = cur.rowcount
    if updated_base:
        conn.commit()
        print(f"  Atualizados {updated_base} combination_indices de produtos base")

    t0 = time.time()
    migrated = 0
    untouched = 0
    errors = 0

    for r in rows:
        pp_id = r[0]
        commercial_tmpl_id = r[1]
        new_tmpl_id = r[2]
        cod_sx = r[4]

        if pp_id in existing_under_tech:
            untouched += 1
            continue

        # Set combination_indices to ptav_id (unique per variant)
        val_id = value_ids.get(cod_sx) if cod_sx else None
        ptav_id_from_map = ptav_map.get((commercial_tmpl_id, val_id)) if val_id else None
        combo = str(ptav_id_from_map) if ptav_id_from_map else 'pp_' + str(pp_id)

        # Use savepoint per product to isolate errors
        cur.execute("SAVEPOINT prod_sp")
        try:
            cur.execute("""
                UPDATE product_product SET product_tmpl_id = %s, combination_indices = %s WHERE id = %s
            """, (new_tmpl_id, combo, pp_id))
            cur.execute("RELEASE SAVEPOINT prod_sp")

            migrated += 1
            if migrated % 1000 == 0:
                conn.commit()
                elapsed = time.time() - t0
                print(f"    {migrated} migrados ({elapsed:.0f}s)")

        except Exception as e:
            cur.execute("ROLLBACK TO SAVEPOINT prod_sp")
            errors += 1
            if errors <= 5:
                print(f"    ERRO pp_id={pp_id}: {e}")

    print(f"  Migrados: {migrated}, Ja existentes: {untouched}, Erros: {errors}")


def limpar_templates_orfandos(cur):
    """Desativa templates comerciais que perderam todos product_product"""
    cur.execute("""
        SELECT pt.id, pt.default_code
        FROM product_template pt
        WHERE pt.default_code ~ '^[0-9]{3}\.[0-9]{3}\.'
          AND NOT EXISTS (SELECT 1 FROM product_product pp WHERE pp.product_tmpl_id = pt.id)
    """)
    orphans = cur.fetchall()
    print(f"  Templates orfaos para desativar: {len(orphans)}")

    t0 = time.time()
    for r in orphans:
        cur.execute("UPDATE product_template SET active = false WHERE id = %s", (r[0],))
    print(f"  Desativados em {time.time()-t0:.0f}s")


def verificar(cur):
    cur.execute("""
        SELECT
            COUNT(pp.id) AS total_pp,
            SUM(CASE WHEN pt.default_code ~ '^[0-9]{3}\.[0-9]{3}$' THEN 1 ELSE 0 END) AS sob_tecnicos,
            SUM(CASE WHEN pt.default_code ~ '^[0-9]{3}\.[0-9]{3}\.' THEN 1 ELSE 0 END) AS sob_comerciais,
            SUM(CASE WHEN pt.active = false THEN 1 ELSE 0 END) AS inativos
        FROM product_product pp
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
    """)
    r = cur.fetchone()
    print(f"  Total product.products: {r[0]}")
    print(f"  Sob templates tecnicos: {r[1]}")
    print(f"  Sob templates comerciais: {r[2]}")
    print(f"  Em templates inativos: {r[3]}")

    for tbl in ['product_template_attribute_line', 'product_template_attribute_value']:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        print(f"  {tbl}: {cur.fetchone()[0]}")


def main():
    if DRY_RUN:
        print("*** MODO DRY-RUN ***\n")

    conn = psycopg2.connect(**ODOO_PG)
    cur = conn.cursor()

    print("=== 1. Atributo 'Codigo Variante' ===")
    if not DRY_RUN:
        attr_id, value_ids = criar_atributo_variante(cur)
        conn.commit()

    print("\n=== 2. Attribute lines ===")
    ptav_map = {}
    if not DRY_RUN:
        ptav_map = criar_attribute_lines(cur, attr_id, value_ids)
        conn.commit()

    print("\n=== 3. Migrando product.products ===")
    if not DRY_RUN:
        migrar_product_products(conn, cur, value_ids, ptav_map)
        conn.commit()

    print("\n=== 4. Limpando templates orfaos ===")
    if not DRY_RUN:
        limpar_templates_orfandos(cur)
        conn.commit()

    print("\n=== 5. Verificacao ===")
    verificar(cur)

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
