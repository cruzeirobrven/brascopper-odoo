#!/usr/bin/env python3
"""
Importa mapeamento ESTPRO → catálogo técnico (IT_PX/IT_CO/IT_SX/IT_BI)
e popula technical_template_id no Odoo.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pymssql
import psycopg2
from psycopg2.extras import execute_values

SQL = {
    'server': '100.64.83.82:1433',
    'user': 'sa',
    'password': 'MULETA',
    'database': 'brven_brascopper',
    'charset': 'utf8',
    'timeout': 30,
}

PG_LOCAL = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')
ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')


def importar_mapping():
    print("=== Importando ESTPRO IT_PX/IT_CO mapping ===")
    conn = pymssql.connect(**SQL)
    cur = conn.cursor()
    cur.execute("""
        SELECT RTRIM(PRODUTO) AS codigo_erp,
               RTRIM(IT_PX) AS it_px,
               RTRIM(IT_CO) AS it_co,
               RTRIM(IT_SX) AS it_sx,
               RTRIM(IT_BI) AS it_bi
        FROM ESTPRO
    """)
    rows = cur.fetchall()
    conn.close()
    print(f"  Lidos {len(rows)} registros do SQL Server")

    pg = psycopg2.connect(**PG_LOCAL)
    cur = pg.cursor()
    cur.execute("TRUNCATE erp_produto_tecnico_mapping")
    data = [(r[0], r[1], r[2], r[3], r[4]) for r in rows]
    execute_values(cur, """
        INSERT INTO erp_produto_tecnico_mapping (codigo_erp, it_px, it_co, it_sx, it_bi)
        VALUES %s
    """, data, page_size=1000)
    pg.commit()
    cur.execute("SELECT COUNT(*) FROM erp_produto_tecnico_mapping")
    print(f"  Inseridos {cur.fetchone()[0]} registros no PostgreSQL")
    pg.close()


def popular_technical_template_id():
    print("\n=== Populando technical_template_id no Odoo ===")
    pg = psycopg2.connect(**ODOO_PG)
    cur = pg.cursor()

    # Add column if not exists
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'product_template' AND column_name = 'technical_default_code'
    """)
    if not cur.fetchone():
        cur.execute("ALTER TABLE product_template ADD COLUMN technical_default_code VARCHAR")
        cur.execute("CREATE INDEX IF NOT EXISTS product_template_technical_default_code_idx ON product_template(technical_default_code)")
        pg.commit()
        print("  Coluna technical_default_code adicionada")

    # Build mapping from erp_produto_tecnico_mapping
    pg_local = psycopg2.connect(**PG_LOCAL)
    cur_local = pg_local.cursor()
    cur_local.execute("""
        SELECT m.codigo_erp,
               LPAD(COALESCE(NULLIF(TRIM(m.it_px), ''), '0'), 3, '0') || '.' ||
               LPAD(COALESCE(NULLIF(TRIM(m.it_co), ''), '0'), 3, '0') AS codigo_tecnico
        FROM erp_produto_tecnico_mapping m
        WHERE m.it_px IS NOT NULL AND m.it_co IS NOT NULL
          AND TRIM(m.it_px) != '' AND TRIM(m.it_co) != ''
    """)
    mapping = {}
    for row in cur_local.fetchall():
        mapping[row[0]] = row[1]
    pg_local.close()
    print(f"  Mapping IT_PX/IT_CO: {len(mapping)} registros")

    # Also build mapping from PRODUTO prefix (first 7 chars)
    cur_local = psycopg2.connect(**PG_LOCAL).cursor()
    cur_local.execute("""
        SELECT DISTINCT codigo_erp, LEFT(codigo_erp, 7) AS prefixo
        FROM erp_produtos
        WHERE codigo_erp ~ '^[0-9]{3}\.[0-9]{3}\.'
    """)
    prefix_map = {}
    for row in cur_local.fetchall():
        prefix_map[row[0]] = row[1]
    cur_local.connection.close()
    print(f"  Mapping PRODUTO prefix: {len(prefix_map)} registros")

    # Get all technical templates
    cur.execute("SELECT id, default_code FROM product_template WHERE default_code ~ '^[0-9]{3}\.[0-9]{3}$'")
    tech_templates = {r[1]: r[0] for r in cur.fetchall()}
    print(f"  Templates tecnicos: {len(tech_templates)}")

    # For each commercial product, determine technical template code
    cur.execute("""
        SELECT pt.id, pt.default_code
        FROM product_template pt
        WHERE pt.default_code IS NOT NULL
          AND pt.default_code ~ '^[0-9]{3}\.[0-9]{3}\.'
    """)
    to_update = []
    matched_it = 0
    matched_prefix = 0
    not_matched = 0
    for row in cur.fetchall():
        prod_id = row[0]
        prod_code = row[1]

        # Priority 1: IT_PX/IT_CO mapping
        tech_code = mapping.get(prod_code)
        if tech_code and tech_code in tech_templates:
            to_update.append((tech_code, prod_id))
            matched_it += 1
            continue

        # Priority 2: PRODUTO prefix (first 7 chars)
        prefix = prefix_map.get(prod_code)
        if not prefix:
            prefix = prod_code[:7]
        if prefix in tech_templates:
            to_update.append((prefix, prod_id))
            matched_prefix += 1
            continue

        not_matched += 1

    print(f"  Match IT_PX/IT_CO: {matched_it}")
    print(f"  Match prefixo: {matched_prefix}")
    print(f"  Sem match: {not_matched}")
    print(f"  Total para atualizar: {len(to_update)}")

    # Update technical_default_code
    t0 = time.time()
    updated = 0
    batch = []
    for tech_code, prod_id in to_update:
        batch.append((tech_code, prod_id))
        if len(batch) >= 1000:
            execute_values(cur, """
                UPDATE product_template SET technical_default_code = data.tech_code
                FROM (VALUES %s) AS data(tech_code, prod_id)
                WHERE product_template.id = data.prod_id
            """, batch, page_size=1000)
            pg.commit()
            updated += len(batch)
            batch = []
            if updated % 10000 == 0:
                print(f"    {updated} atualizados ({time.time()-t0:.0f}s)")

    if batch:
        execute_values(cur, """
            UPDATE product_template SET technical_default_code = data.tech_code
            FROM (VALUES %s) AS data(tech_code, prod_id)
            WHERE product_template.id = data.prod_id
        """, batch, page_size=1000)
        pg.commit()
        updated += len(batch)

    print(f"  Atualizados {updated} products em {time.time()-t0:.0f}s")
    cur.close()
    pg.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--skip-import', action='store_true', help='Pular importacao do SQL Server')
    args = parser.parse_args()

    if not args.skip_import:
        importar_mapping()
    popular_technical_template_id()
