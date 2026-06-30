#!/usr/bin/env python3
"""
Sincronizacao incremental via funcoes PL/pgSQL no PostgreSQL do Odoo.
~100x mais rapido que XML-RPC.

Uso:
  python3 sincronizar_odoo.py                    # tudo
  python3 sincronizar_odoo.py --tabelas clientes  # so clientes
  python3 sincronizar_odoo.py --tabelas produtos  # so produtos
"""
import sys, json, time
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
import psycopg2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from api.database import get_cursor

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
STATE_FILE = Path("/tmp/odoo_sync_state.json")
BATCH_SIZE = 2000


def dict_from_cursor(cur):
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def esc(val):
    """Escapa string para SQL single-quoted string"""
    if val is None:
        return 'NULL'
    return "'" + str(val).replace("'", "''") + "'"


def sinc_produtos():
    print("  --- Produtos (via upsert_product) ---")
    conn = psycopg2.connect(**ODOO_PG)
    cur = conn.cursor()

    with get_cursor() as c:
        c.execute("SELECT * FROM erp_produtos ORDER BY codigo_erp")
        rows = dict_from_cursor(c)

    created = updated = 0
    t0 = time.time()

    for r in rows:
        code = str(r.get('codigo_erp') or '').strip()
        if not code:
            continue

        name = r.get('descricao') or 'Sem Nome'
        name = name[:200]
        price = float(r.get('preco_venda') or 0.0)
        barcode = r.get('codigo_barras') or ''
        active = 'true' if r.get('ativo') else 'false'
        ncm = r.get('ncm') or ''

        cur.execute(f"""
            SELECT upsert_product(
                {esc(code)}, {esc(name)}, {price},
                {esc(barcode)}, {active}, {esc(ncm)}
            )
        """)
        result = cur.fetchone()[0]

        if result > 0:
            # Can't easily distinguish created vs updated from this function
            pass
        created += 1

        if created % 5000 == 0:
            conn.commit()
            elapsed = time.time() - t0
            print(f"    {created}/{len(rows)} ({created/elapsed:.0f}/s)")

    conn.commit()
    cur.close()
    conn.close()
    print(f"  {created} produtos processados em {time.time()-t0:.0f}s")


def sinc_clientes():
    print("  --- Clientes (via upsert_partner) ---")
    conn = psycopg2.connect(**ODOO_PG)
    cur = conn.cursor()

    with get_cursor() as c:
        c.execute("SELECT * FROM erp_clientes ORDER BY codigo_erp")
        rows = dict_from_cursor(c)

    created = 0
    t0 = time.time()

    for r in rows:
        doc = (r.get('cnpj_cpf') or '').replace('.', '').replace('/', '').replace('-', '')
        ext = f"cliente_{r['empresa_erp']}_{r['codigo_erp']}"
        name = (r.get('nome') or 'Sem Nome')[:150].replace("'", "''")
        rg = (r.get('inscricao_rg') or '').replace("'", "''")
        street = (r.get('endereco') or '').replace("'", "''")
        street2 = ((r.get('numero') or '') + ' ' + (r.get('complemento') or '')).strip().replace("'", "''")
        city = (r.get('cidade') or '').replace("'", "''")
        state_uf = r.get('estado') or ''
        zip_val = (r.get('cep') or '').replace('.', '').replace('-', '')[:10]
        phone = (r.get('fone_1') or r.get('fone_2') or '').replace("'", "''")
        email = (r.get('email') or '').replace("'", "''")
        is_company = 'true' if len(doc) > 11 else 'false'
        active = 'true' if r.get('ativo') else 'false'

        cur.execute(f"""
            SELECT upsert_partner(
                {esc(ext)}, {esc(name)}, {esc(doc)}, {esc(rg)},
                {esc(street)}, {esc(street2)}, {esc(city)}, {esc(state_uf)},
                {esc(zip_val)}, {esc(phone)}, {esc(email)},
                {is_company}, {active}
            )
        """)
        created += 1

        if created % 5000 == 0:
            conn.commit()
            elapsed = time.time() - t0
            print(f"    {created}/{len(rows)} ({created/elapsed:.0f}/s)")

    conn.commit()
    cur.close()
    conn.close()
    print(f"  {created} clientes processados em {time.time()-t0:.0f}s")


def sinc_empresas():
    print("  --- Empresas (via upsert_partner) ---")
    conn = psycopg2.connect(**ODOO_PG)
    cur = conn.cursor()

    with get_cursor() as c:
        c.execute("SELECT * FROM erp_empresas")
        rows = dict_from_cursor(c)

    created = 0
    t0 = time.time()

    for r in rows:
        cnpj = (r.get('cnpj') or '').replace('.', '').replace('/', '').replace('-', '')
        ext = f"empresa_{r['codigo_erp']}"
        name = (r.get('nome') or 'Sem Nome')[:150].replace("'", "''")
        rg = (r.get('inscricao_estadual') or '').replace("'", "''")
        street = (r.get('endereco') or '').replace("'", "''")
        street2 = ((r.get('numero') or '') + ' ' + (r.get('complemento') or '')).strip().replace("'", "''")
        city = (r.get('cidade') or '').replace("'", "''")
        state_uf = r.get('estado') or ''
        zip_val = r.get('cep') or ''
        phone = (r.get('fone') or '').replace("'", "''")
        email = (r.get('email') or '').replace("'", "''")

        cur.execute(f"""
            SELECT upsert_partner(
                {esc(ext)}, {esc(name)}, {esc(cnpj)}, {esc(rg)},
                {esc(street)}, {esc(street2)}, {esc(city)}, {esc(state_uf)},
                {esc(zip_val)}, {esc(phone)}, {esc(email)},
                true, true
            )
        """)
        created += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"  {created} empresas processados em {time.time()-t0:.0f}s")


TABELAS = {
    'empresas': sinc_empresas,
    'clientes': sinc_clientes,
    'produtos': sinc_produtos,
}


def main(tabelas=None):
    if tabelas is None:
        tabelas = list(TABELAS.keys())

    print("=" * 50)
    print("Sincronizando via PL/pgSQL no PostgreSQL do Odoo")
    print(f"Tabelas: {', '.join(tabelas)}")
    print("=" * 50)

    for nome in tabelas:
        t0 = time.time()
        TABELAS[nome]()
        print(f"  {nome} feito em {time.time()-t0:.0f}s")

    STATE_FILE.write_text(json.dumps({
        'ultima_execucao': datetime.now().isoformat(),
        'tabelas': tabelas,
    }, default=str))
    print("\nConcluido!")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sincroniza ERP → Odoo via SQL')
    parser.add_argument('--tabelas', nargs='+', help='Tabelas (padrao: todas)')
    args = parser.parse_args()
    main(args.tabelas)
