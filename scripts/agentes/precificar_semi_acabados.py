#!/usr/bin/env python3
"""
Precifica semi-acabados (cordas de cobre, fios de aco, veias, etc.)
que nao tem BOM com componentes reais — usam placeholder 999.997.

Calculo: prokg (kg/m) x preco materia-prima (R$/kg) x markup (1.15)

Markup de 15% cobre custos de transformacao (trefilacao, encordoamento).

Uso: python3 precificar_semi_acabados.py [--dry-run] [--verbose]
"""
import sys, json, time, os
from datetime import date, datetime
import psycopg2

LOG_FILE = '/opt/nfelazarus/logs/historico_precos.jsonl'

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
PDD_PG = dict(host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd')
NFEHUB_PG = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')

DRY_RUN = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv

MARKUP = 1.15  # 15% transformacao

# Mapeamento: tipo de material → codigos raw-material em legacy_proda
RAW_MATERIALS = {
    'cobre':  ('999', '101'),   # preco do cobre R$/kg
    'aco':    ('999', '550'),   # fio de aco galvanizado R$/kg
    'aluminio': ('999', '519'), # aluminio vergalhao R$/kg
}

# Padroes de codigo por tipo
# Codigos que comecam com estes prefixos sao considerados do tipo
CODE_PATTERNS = {
    'cobre':    ['191', '192', '193', '194', '195', '196', '197', '198'],
    'aco':      ['279', '280', '291'],
    'aluminio': ['289', '299', '300'],
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


def get_raw_material_prices(cur_pdd):
    """Busca precos atualizados das materias-primas no legacy_proda."""
    prices = {}
    for tipo, (px, co) in RAW_MATERIALS.items():
        cur_pdd.execute(
            "SELECT presi FROM legacy_proda WHERE pi_px = %s AND pi_co = %s AND presi > 0",
            (px, co)
        )
        row = cur_pdd.fetchone()
        if row:
            prices[tipo] = float(row[0])
        else:
            prices[tipo] = 0.0
    return prices


def get_product_weight(cur_pdd, cur_nfe, px, co):
    """Tenta obter peso (kg/m) do produto de multiplas fontes."""
    # 1. legacy_proda.prokg
    cur_pdd.execute(
        "SELECT prokg FROM legacy_proda WHERE pi_px = %s AND pi_co = %s",
        (px, co)
    )
    row = cur_pdd.fetchone()
    if row and row[0] and float(row[0]) > 0:
        return float(row[0])

    # 2. erp_catalogo_tecnico.peso_kg
    cur_nfe.execute(
        "SELECT peso_kg FROM erp_catalogo_tecnico WHERE pi_px = %s AND pi_co = %s",
        (px, co)
    )
    row = cur_nfe.fetchone()
    if row and row[0] and float(row[0]) > 0:
        return float(row[0])

    return None


def classify_product(code):
    """Classifica o tipo de material pelo prefixo do codigo."""
    prefix = code.split('.')[0]
    for tipo, prefixes in CODE_PATTERNS.items():
        if prefix in prefixes:
            return tipo
    return None


def main():
    t0 = time.time()
    print(f"{'DRY RUN - ' if DRY_RUN else ''}Precificar Semi-Acabados")
    print("=" * 50)

    conn_pdd = psycopg2.connect(**PDD_PG)
    cur_pdd = conn_pdd.cursor()
    conn_nfe = psycopg2.connect(**NFEHUB_PG)
    cur_nfe = conn_nfe.cursor()
    conn_odoo = psycopg2.connect(**ODOO_PG)
    cur_odoo = conn_odoo.cursor()

    # 1. Precos das materias-primas
    raw_prices = get_raw_material_prices(cur_pdd)
    for tipo, preco in raw_prices.items():
        print(f"  Preco {tipo}: R$ {preco:.4f}/kg")
    print()

    if any(p == 0 for p in raw_prices.values()):
        print("ERRO: materia-prima sem preco. Execute sync_legacy_prices.py primeiro.")
        return

    # 2. Busca produtos Odoo com BOM que estao sem preco (os 161)
    cur_odoo.execute("""
        SELECT DISTINCT pt.default_code, pt.id, pt.name
        FROM product_template pt
        WHERE pt.active = true
        AND pt.default_code IS NOT NULL AND pt.default_code != ''
        AND EXISTS (SELECT 1 FROM mrp_bom b WHERE b.product_tmpl_id = pt.id AND b.active = true)
        AND NOT EXISTS (
            SELECT 1 FROM product_product pp 
            WHERE pp.product_tmpl_id = pt.id AND pp.active = true
            AND pp.standard_price IS NOT NULL
            AND pp.standard_price::text NOT IN ('null', '0', '[0,1]')
        )
        ORDER BY pt.default_code
    """)
    produtos = [r for r in cur_odoo.fetchall()]
    print(f"Templates sem preco (com BOM): {len(produtos)}")

    # 3. Currency ID
    cur_odoo.execute("SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1")
    currency_id = cur_odoo.fetchone()[0]

    atualizados = 0
    sem_peso = 0
    nao_classificado = 0
    erros = 0
    today = date.today()

    for tmpl_code, tmpl_id, tmpl_name in produtos:
        tipo = classify_product(tmpl_code)
        if not tipo:
            nao_classificado += 1
            if VERBOSE:
                print(f"  ? {tmpl_code}: tipo nao classificado")
            continue

        px, co = tmpl_code.split('.')
        peso = get_product_weight(cur_pdd, cur_nfe, px, co)
        if not peso or peso <= 0:
            sem_peso += 1
            if VERBOSE:
                print(f"  ? {tmpl_code}: sem peso cadastrado")
            continue

        raw_price = raw_prices[tipo]
        custo = round(peso * raw_price * MARKUP, 4)

        try:
            if not DRY_RUN:
                json_price = json.dumps([custo, currency_id])
                cur_odoo.execute("""
                    UPDATE product_product 
                    SET standard_price = %s::jsonb, write_date = NOW()
                    WHERE product_tmpl_id = %s AND active = true
                """, (json_price, tmpl_id))
                log_preco('semi_acabado', tmpl_code, custo,
                          f'prokg={peso} x R${raw_price}/kg x {MARKUP} ({tipo})')
            atualizados += 1
            if VERBOSE:
                print(f"  ✓ R$ {custo:.4f}  {tmpl_code}  ({peso}kg x R${raw_price})")
        except Exception as e:
            erros += 1
            print(f"  ERRO {tmpl_code}: {e}")

        if not DRY_RUN and atualizados % 100 == 0:
            conn_odoo.commit()
            elapsed = time.time() - t0
            print(f"  ... {atualizados} atualizados ({elapsed:.0f}s)")

    if not DRY_RUN:
        conn_odoo.commit()

    elapsed = time.time() - t0
    print()
    print("=" * 50)
    print(f"Tempo: {elapsed:.0f}s")
    print(f"Atualizados (prokg x preco MP x {MARKUP}): {atualizados}")
    print(f"Sem peso cadastrado: {sem_peso}")
    print(f"Nao classificado: {nao_classificado}")
    print(f"Erros: {erros}")
    if DRY_RUN:
        print("\nUse sem --dry-run para aplicar.")

    cur_pdd.close()
    conn_pdd.close()
    cur_nfe.close()
    conn_nfe.close()
    cur_odoo.close()
    conn_odoo.close()


if __name__ == '__main__':
    main()
