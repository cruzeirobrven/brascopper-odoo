#!/usr/bin/env python3
"""
Sincroniza precos de materias-primas do pro_preco_material_legacy → legacy_proda.presi.

Le o preco mais recente (R$/kg) de cada material 999.xxx cadastrado no
historico mensal e atualiza a tabela legacy_proda, que alimenta o calculo
de custo de BOM no Odoo.

Materiais de cobre (999.101-103) e aluminio (999.518,519,530,532) sao
PULADOS — sao atualizados pelo agente de cotacoes de commodities.

Uso: python3 sync_legacy_prices.py [--dry-run] [--verbose]
"""
import sys, json, time, os
from datetime import date, datetime
import psycopg2

LOG_FILE = '/opt/nfelazarus/logs/historico_precos.jsonl'

PDD_PG = dict(host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd')

DRY_RUN = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv

SKIP_CODES = {
    ('999', '101'), ('999', '102'), ('999', '103'),
    ('999', '518'), ('999', '519'), ('999', '530'), ('999', '532'),
}


def log_preco(source, produto_cod, preco, detalhe=''):
    entry = {
        'ts': datetime.now().isoformat(),
        'fonte': source,
        'produto': produto_cod,
        'preco': round(preco, 4),
        'detalhe': detalhe,
    }
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def main():
    t0 = time.time()
    print(f"{'DRY RUN - ' if DRY_RUN else ''}Sync Precos Materias-Primas (Legado → legacy_proda)")
    print("=" * 55)

    conn = psycopg2.connect(**PDD_PG)
    cur = conn.cursor()

    cur.execute("""
        SELECT pi_px, pi_co, descr, anome, preco
        FROM pro_preco_material_legacy
        WHERE (pi_px, pi_co, anome) IN (
            SELECT pi_px, pi_co, MAX(anome)
            FROM pro_preco_material_legacy
            WHERE preco > 0
            GROUP BY pi_px, pi_co
        )
        ORDER BY pi_px, pi_co
    """)
    rows = cur.fetchall()
    print(f"Materials com precos no pro_preco_material_legacy: {len(rows)}")

    atualizados = 0
    pulados = 0
    inexistentes = 0
    erros = 0
    today = date.today()

    for px, co, descr, anome, preco in rows:
        cod = f"{px}.{co}"

        if (px, co) in SKIP_CODES:
            if VERBOSE:
                print(f"  - {cod}: pulado (commodities)")
            pulados += 1
            continue

        cur.execute(
            "SELECT 1 FROM legacy_proda WHERE pi_px = %s AND pi_co = %s",
            (px, co)
        )
        if not cur.fetchone():
            inexistentes += 1
            if VERBOSE:
                print(f"  ? {cod}: nao encontrado em legacy_proda")
            continue

        try:
            preco_float = float(preco)
            if not DRY_RUN:
                cur.execute(
                    "UPDATE legacy_proda SET presi = %s, prdat = %s "
                    "WHERE pi_px = %s AND pi_co = %s",
                    (preco_float, today, px, co)
                )
                log_preco('legacy_material_legacy', cod, preco_float,
                          f'pro_preco_material_legacy ({anome})')
            atualizados += 1
            if VERBOSE:
                print(f"  ✓ R$ {preco_float:.4f}/kg  {cod}  {descr}")
        except Exception as e:
            erros += 1
            print(f"  ERRO {cod}: {e}")

    conn.commit()
    cur.close()
    conn.close()

    elapsed = time.time() - t0
    print()
    print("=" * 55)
    print(f"Tempo: {elapsed:.0f}s")
    print(f"Atualizados: {atualizados}")
    print(f"Pulados (commodities): {pulados}")
    print(f"Nao encontrados em legacy_proda: {inexistentes}")
    print(f"Erros: {erros}")
    if DRY_RUN:
        print("\nUse sem --dry-run para aplicar.")


if __name__ == '__main__':
    main()
