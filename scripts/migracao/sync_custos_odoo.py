#!/usr/bin/env python3
"""
Calcula custo padrão dos produtos no Odoo com base na BOM + preços dos componentes.

Fluxo:
1. Lê BOMs do Odoo (mrp_bom + mrp_bom_line)
2. Para cada componente, obtém standard_price (product_product.standard_price JSONB)
3. Se não disponível, busca preço em erp_precos_mp (nfehub) × peso_kg (catálogo técnico)
4. Calcula custo total = Σ (qtd_componente × preco_unitario_componente)
5. Atualiza product_product.standard_price para todos os product_product do template

Uso: python3 sync_custos_odoo.py [--dry-run] [--verbose]
"""
import sys, json, time
from collections import defaultdict
import psycopg2
import psycopg2.extras

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
NFEHUB_PG = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')
PDD_PG = dict(host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd')

DRY_RUN = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv


def extract_price_from_jsonb(val):
    """Extrai valor numérico do JSONB monetary do Odoo 18.
    Formatos possíveis: [price, currency_id] ou {"price": price} ou null"""
    if val is None:
        return 0.0
    if isinstance(val, list) and len(val) >= 1:
        return float(val[0])
    if isinstance(val, dict):
        return float(val.get('price', 0))
    if isinstance(val, (int, float)):
        return float(val)
    return 0.0


def conectar_odoo():
    return psycopg2.connect(**ODOO_PG)


def conectar_nfehub():
    return psycopg2.connect(**NFEHUB_PG)


def carregar_pesos_bom_pdd():
    """Carrega peso_unit_kg de cada linha da BOM no PDD para conversao g→kg."""
    try:
        conn_pdd = psycopg2.connect(**PDD_PG)
        cur_pdd = conn_pdd.cursor()
        cur_pdd.execute("""
            SELECT prod_px, prod_co, comp_px, comp_co, unidade, peso_unit_kg
            FROM pro_bom_cabo_legacy
            WHERE unidade = 'g' AND peso_unit_kg > 0
        """)
        pesos = {}
        for prod_px, prod_co, comp_px, comp_co, unidade, peso in cur_pdd:
            prod_cod = f"{prod_px}.{prod_co}"
            comp_cod = f"{comp_px}.{comp_co}"
            key = (prod_cod, comp_cod)
            pesos[key] = float(peso)
        cur_pdd.close()
        conn_pdd.close()
        return pesos
    except Exception as e:
        print(f"  AVISO: nao foi possivel carregar pesos da BOM PDD: {e}")
        return {}


def carregar_precos_componentes(cur_nfehub):
    # Tenta primeiro do brascopper_pdd (legacy_proda - dados mais completos)
    try:
        conn_pdd = psycopg2.connect(**PDD_PG)
        cur_pdd = conn_pdd.cursor()
        cur_pdd.execute("""
            SELECT pi_px, pi_co, presi FROM legacy_proda WHERE presi > 0
        """)
        precos = {f"{px}.{co}": float(presi) for px, co, presi in cur_pdd}
        cur_pdd.close()
        conn_pdd.close()
        if precos:
            return precos
    except Exception:
        pass

    # Fallback: erp_precos_mp do nfehub
    cur_nfehub.execute("""
        SELECT DISTINCT ON (pi_px, pi_co) 
            pi_px, pi_co, preco_kg
        FROM erp_precos_mp
        WHERE preco_kg > 0
        ORDER BY pi_px, pi_co, ano_mes DESC
    """)
    return {f"{px}.{co}": float(preco) for px, co, preco in cur_nfehub}


def carregar_pesos_catalogo(cur_nfehub):
    cur_nfehub.execute("""
        SELECT pi_px, pi_co, peso_kg FROM erp_catalogo_tecnico
        WHERE peso_kg IS NOT NULL AND peso_kg > 0
    """)
    return {f"{px}.{co}": float(peso) for px, co, peso in cur_nfehub}


def carregar_boms_odoo(cur_odoo):
    """Carrega BOMs com preço do componente via product_product.standard_price (JSONB)."""
    cur_odoo.execute("""
        SELECT 
            b.id AS bom_id,
            b.product_tmpl_id,
            pt.default_code AS tmpl_code,
            bl.id AS line_id,
            bl.product_id,
            bl.product_qty,
            pp.default_code AS comp_variant_code,
            ppt.id AS comp_tmpl_id,
            ppt.default_code AS comp_tmpl_code,
            pp.standard_price AS comp_standard_price_raw
        FROM mrp_bom b
        JOIN product_template pt ON pt.id = b.product_tmpl_id
        JOIN mrp_bom_line bl ON bl.bom_id = b.id
        JOIN product_product pp ON pp.id = bl.product_id
        JOIN product_template ppt ON ppt.id = pp.product_tmpl_id
        WHERE b.active = true
        ORDER BY b.id, bl.sequence
    """)
    boms = defaultdict(list)
    for row in cur_odoo:
        r = dict(row)
        raw = row['comp_standard_price_raw']
        r['comp_standard_price'] = extract_price_from_jsonb(raw)
        boms[row['bom_id']].append(r)
    return boms


def carregar_standard_prices_odoo(cur_odoo):
    """Carrega todos os standard_price dos product_product como fallback."""
    cur_odoo.execute("SELECT id, standard_price FROM product_product")
    precos = {}
    for pp_id, raw in cur_odoo:
        val = extract_price_from_jsonb(raw)
        if val > 0:
            precos[pp_id] = val
    return precos


def calcular_custo_bom(bom_lines, precos_mp, pesos_catalogo, precos_pp, pesos_bom_pdd):
    """Calcula o custo total de uma BOM."""
    custo_total = 0.0
    detalhes = []
    for line in bom_lines:
        qtd = float(line['product_qty'])
        comp_tmpl_code = line['comp_tmpl_code']
        tmpl_code = line.get('tmpl_code', '')
        comp_price = line['comp_standard_price']

        if comp_price == 0 and comp_tmpl_code in precos_mp:
            price_kg = precos_mp[comp_tmpl_code]
            # Tenta peso da propria BOM no PDD (mais preciso, com unidade g→kg)
            peso_bom = pesos_bom_pdd.get((tmpl_code, comp_tmpl_code), 0)
            if peso_bom > 0:
                comp_price = price_kg * peso_bom
            else:
                peso = pesos_catalogo.get(comp_tmpl_code, 0)
                comp_price = price_kg * peso if peso > 0 else price_kg

        contrib = qtd * comp_price
        custo_total += contrib

        if VERBOSE:
            detalhes.append({
                'codigo': comp_tmpl_code,
                'qtd': qtd,
                'preco': comp_price,
                'contrib': contrib,
            })
    return custo_total, detalhes


def main():
    t0 = time.time()
    print(f"{'DRY RUN - ' if DRY_RUN else ''}Sync de Custos Odoo ← BOM")
    print("=" * 50)

    conn_nfe = conectar_nfehub()
    cur_nfe = conn_nfe.cursor()
    precos_mp = carregar_precos_componentes(cur_nfe)
    pesos_catalogo = carregar_pesos_catalogo(cur_nfe)
    cur_nfe.close()
    conn_nfe.close()
    print(f"Preços MP (erp_precos_mp): {len(precos_mp)} produtos")
    print(f"Pesos catálogo técnico: {len(pesos_catalogo)} produtos")

    pesos_bom_pdd = carregar_pesos_bom_pdd()
    print(f"Pesos BOM PDD (g→kg): {len(pesos_bom_pdd)} linhas")

    conn_odoo = conectar_odoo()
    cur_odoo = conn_odoo.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    boms = carregar_boms_odoo(cur_odoo)
    cur_odoo.close()
    print(f"BOMs ativas carregadas: {len(boms)}")

    cur_odoo2 = conn_odoo.cursor()
    cur_odoo2.execute("SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1")
    currency_id = cur_odoo2.fetchone()[0]
    cur_odoo2.close()

    conn_odoo2 = conectar_odoo()
    cur_upd = conn_odoo2.cursor()
    atualizados = 0
    sem_preco = 0
    erros = 0

    for bom_id, lines in sorted(boms.items()):
        tmpl_id = lines[0]['product_tmpl_id']
        tmpl_code = lines[0]['tmpl_code']

        custo, detalhes = calcular_custo_bom(lines, precos_mp, pesos_catalogo, precos_pp={}, pesos_bom_pdd=pesos_bom_pdd)

        if custo == 0:
            sem_preco += 1
            if VERBOSE:
                print(f"  ⚠ {tmpl_code} (BOM {bom_id}): custo = 0 (sem preço nos componentes)")
            continue

        try:
            if not DRY_RUN:
                json_price = json.dumps([round(custo, 4), currency_id])
                cur_upd.execute("""
                    UPDATE product_product 
                    SET standard_price = %s::jsonb, write_date = NOW()
                    WHERE product_tmpl_id = %s AND active = true
                """, (json_price, tmpl_id))
            atualizados += 1

            if VERBOSE and detalhes:
                comps = ', '.join(f"{d['codigo']}={d['contrib']:.4f}" for d in detalhes[:5])
                print(f"  ✓ {tmpl_code}: custo = {custo:.4f} ({comps})")

            if not DRY_RUN and atualizados % 500 == 0:
                conn_odoo2.commit()
                elapsed = time.time() - t0
                print(f"  ... {atualizados} templates atualizados ({elapsed:.0f}s)")

        except Exception as e:
            erros += 1
            print(f"  ERRO {tmpl_code}: {e}")

    if not DRY_RUN:
        conn_odoo2.commit()

    cur_upd.close()
    conn_odoo2.close()
    conn_odoo.close()

    elapsed = time.time() - t0
    print()
    print("=" * 50)
    print(f"Tempo: {elapsed:.0f}s")
    print(f"Templates atualizados: {atualizados}")
    print(f"Sem preço (custo=0): {sem_preco}")
    print(f"Erros: {erros}")
    if DRY_RUN:
        print("\nUse sem --dry-run para aplicar.")


if __name__ == '__main__':
    main()
