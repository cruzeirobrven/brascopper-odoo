#!/usr/bin/env python3
"""
Extrai precos de compra (COMNOT+COMCIT) para produtos comerciais sem standard_price.

Fluxo:
1. Conecta Odoo PG e brascopper_pdd
2. Identifica product.product (variantes comerciais) sem standard_price
3. Busca precos de compra recentes em recebimentos_erp_item_nf_direto
4. Calcula preco medio ponderado (ultimos 12 meses)
5. Atualiza standard_price no Odoo

Uso: python3 extrair_precos_compras.py [--dry-run] [--verbose]
"""
import sys, json, time
from collections import defaultdict
import psycopg2

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
PDD_PG = dict(host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd')

DRY_RUN = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv


def extract_price_from_jsonb(val):
    if val is None:
        return 0.0
    if isinstance(val, list) and len(val) >= 1:
        return float(val[0])
    if isinstance(val, dict):
        return float(val.get('price', 0))
    if isinstance(val, (int, float)):
        return float(val)
    return 0.0


def main():
    t0 = time.time()
    print(f"{'DRY RUN - ' if DRY_RUN else ''}Extrair Precos de Compras (COMCIT)")
    print("=" * 50)

    conn_pdd = psycopg2.connect(**PDD_PG)
    cur_pdd = conn_pdd.cursor()
    conn_odoo = psycopg2.connect(**ODOO_PG)
    cur_odoo = conn_odoo.cursor()

    # 1. Product.products sem standard_price (apenas variantes comerciais XXX.XXX.XX)
    cur_odoo.execute("""
        SELECT pp.id, pp.default_code, pt.default_code AS tmpl_code
        FROM product_product pp
        JOIN product_template pt ON pt.id = pp.product_tmpl_id
        WHERE pp.default_code ~ '^[0-9]{3}\.[0-9]{3}\.'
          AND (pp.standard_price IS NULL
               OR pp.standard_price::text = 'null'
               OR pp.standard_price::text = '0'
               OR pp.standard_price::text = '[0,1]')
          AND pp.active = true
    """)
    products = {r[0]: {'code': r[1], 'tmpl_code': r[2]} for r in cur_odoo.fetchall()}
    print(f"Produtos comerciais sem preco: {len(products)}")

    if not products:
        cur_pdd.close()
        conn_pdd.close()
        cur_odoo.close()
        conn_odoo.close()
        return

    # 2. Carrega precos de compra (ultimos 12 meses)
    cur_pdd.execute("""
        SELECT r.produto, r.quantidade, r.custo, h.entrada
        FROM recebimentos_erp_item_nf_direto r
        JOIN recebimentos_erp_nf_entrada h ON h.registro = r.nf_registro
        WHERE r.custo > 0 AND r.quantidade > 0
          AND h.entrada >= (CURRENT_DATE - INTERVAL '12 months')
        ORDER BY h.entrada DESC
    """)
    rows = cur_pdd.fetchall()
    print(f"Linhas de compra (12 meses): {len(rows)}")

    # 3. Agrupa precos por produto: preco_medio_ponderado
    compras = defaultdict(list)
    for produto, qtd, custo, data in rows:
        q = float(qtd)
        c = float(custo)
        unit_price = c / q if q > 0 else 0
        if unit_price > 0:
            compras[produto.strip()].append((unit_price, q))

    precos_compra = {}
    for code, prices in compras.items():
        total_valor = sum(p[0] * p[1] for p in prices)
        total_qtd = sum(p[1] for p in prices)
        precos_compra[code] = total_valor / total_qtd if total_qtd > 0 else 0

    # 4. Match com produtos Odoo e atualiza
    cur_odoo.execute("SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1")
    currency_id = cur_odoo.fetchone()[0]

    atualizados = 0
    sem_match = 0
    erros = 0

    for pp_id, info in products.items():
        code = info['code'].strip()
        price = precos_compra.get(code)
        if not price:
            sem_match += 1
            continue

        try:
            json_price = json.dumps([round(price, 4), currency_id])
            if not DRY_RUN:
                cur_odoo.execute("""
                    UPDATE product_product
                    SET standard_price = %s::jsonb, write_date = NOW()
                    WHERE id = %s
                """, (json_price, pp_id))
            atualizados += 1
            if VERBOSE and atualizados <= 30:
                print(f"  R$ {price:.4f}  {code}")
        except Exception as e:
            erros += 1
            print(f"  ERRO pp_id={pp_id} ({code}): {e}")

        if not DRY_RUN and atualizados % 500 == 0:
            conn_odoo.commit()
            elapsed = time.time() - t0
            print(f"  ... {atualizados} atualizados ({elapsed:.0f}s)")

    if not DRY_RUN:
        conn_odoo.commit()

    elapsed = time.time() - t0
    print()
    print("=" * 50)
    print(f"Tempo: {elapsed:.0f}s")
    print(f"Produtos analisados: {len(products)}")
    print(f"Atualizados (com preco de compra): {atualizados}")
    print(f"Sem compra nos ultimos 12 meses: {sem_match}")
    print(f"Erros: {erros}")

    cur_pdd.close()
    conn_pdd.close()
    cur_odoo.close()
    conn_odoo.close()


if __name__ == '__main__':
    main()
