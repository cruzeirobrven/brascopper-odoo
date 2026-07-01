#!/usr/bin/env python3
"""
Define precos de venda (list_price) no Odoo a partir do historico de pedidos.

Fluxo:
1. Conecta Odoo PG e brascopper_pdd
2. Agrega valor_unitario × quantidade do com_item_pedido_venda (ultimos N meses)
3. Calcula preco medio ponderado por produto
4. Atualiza list_price no product_template do Odoo
5. Gera catalogo CSV dos top 100 mais vendidos

Uso: python3 precos_venda.py [--meses 24] [--min-pedidos 5] [--dry-run] [--verbose]
"""
import sys, json, time, os, csv
from datetime import datetime, date
from collections import defaultdict
import psycopg2

LOG_FILE = '/opt/nfelazarus/logs/historico_precos.jsonl'
CATALOGO_FILE = '/opt/nfelazarus/logs/catalogo_vendas.csv'

ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
PDD_PG = dict(host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd')

MESES = 24
MIN_PEDIDOS = 5
DRY_RUN = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv

for i, arg in enumerate(sys.argv[1:], 1):
    if arg == '--meses' and i < len(sys.argv):
        MESES = int(sys.argv[i + 1])
    elif arg == '--min-pedidos' and i < len(sys.argv):
        MIN_PEDIDOS = int(sys.argv[i + 1])


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
    label = 'DRY RUN - ' if DRY_RUN else ''
    print(f"{label}Precos de Venda (list_price) ← Historico Pedidos")
    print("=" * 60)

    data_corte = date.today().replace(year=date.today().year - MESES // 12 * (1 if MESES < 24 else MESES // 12)).replace(month=max(1, date.today().month - MESES % 12) if MESES < 12 else 1)
    # Simpler: subtract months
    m = date.today().month - MESES
    y = date.today().year
    while m < 1:
        m += 12
        y -= 1
    data_corte = date(y, m, 1)

    conn_pdd = psycopg2.connect(**PDD_PG)
    cur_pdd = conn_pdd.cursor()
    conn_odoo = psycopg2.connect(**ODOO_PG)
    cur_odoo = conn_odoo.cursor()

    # ── Passo 1: Buscar historico de vendas do legado ──
    print(f"\n>>> 1/4 Agregando vendas desde {data_corte} (min {MIN_PEDIDOS} pedidos)...")
    cur_pdd.execute("""
        SELECT i.it_px, i.it_co,
            SUM(i.valor_total) AS receita_total,
            SUM(i.quantidade) AS qtd_total,
            COUNT(*) AS num_pedidos,
            AVG(i.valor_unitario) AS preco_medio_simples,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY i.valor_unitario) AS mediana
        FROM com_item_pedido_venda i
        JOIN com_pedido_venda p ON p.id = i.pedido_id
        WHERE p.ativo = true AND i.ativo = true
          AND p.data >= %s
          AND i.valor_unitario > 0.01
        GROUP BY i.it_px, i.it_co
        HAVING COUNT(*) >= %s AND SUM(i.quantidade) > 0 AND SUM(i.valor_total) > 0
        ORDER BY SUM(i.valor_total) DESC
    """, (data_corte, MIN_PEDIDOS))

    rows = cur_pdd.fetchall()
    preco_medio = {}  # codigo -> (preco_ponderado, qtd, pedidos, descricao)
    catalogo = []

    MARKUP_MINIMO = 1.30

    for it_px, it_co, receita, qtd, pedidos, media_simples, mediana in rows:
        cod = f"{it_px}.{it_co}"
        preco_pond = round(receita / qtd, 4) if qtd > 0 else 0
        mediana = round(mediana, 4) if mediana else 0
        preco_medio[cod] = {
            'preco': preco_pond,
            'mediana': mediana,
            'qtd': qtd,
            'pedidos': pedidos,
            'media_simples': round(media_simples, 4) if media_simples else 0,
        }

    print(f"  Produtos com historico: {len(preco_medio)}")

    # ── Passo 2: Buscar descricoes e pesos ──
    print(">>> 2/4 Buscando dados tecnicos (descricao, peso)...")
    cur_pdd.execute(
        "SELECT pi_px, pi_co, itdesc, COALESCE(prokg, 0) FROM legacy_proda"
    )
    descricoes = {f"{px}.{co}": (desc, float(peso)) for px, co, desc, peso in cur_pdd}

    # Tambem busca do Odoo para produtos que existem la
    cur_odoo.execute("""
        SELECT pt.default_code, pt.name, pt.list_price,
            (SELECT (pp.standard_price->>0)::numeric
             FROM product_product pp
             WHERE pp.product_tmpl_id = pt.id AND pp.active = true
             LIMIT 1) AS custo
        FROM product_template pt
        WHERE pt.active = true
          AND pt.default_code IS NOT NULL
    """)
    odoo_produtos = {}
    for row in cur_odoo.fetchall():
        cod, name, list_price, custo = row
        if cod:
            odoo_produtos[cod] = {
                'name': name,
                'list_price': float(list_price) if list_price is not None else 0,
                'custo': float(custo) if custo is not None else 0,
            }

    # ── Passo 3: Atualizar list_price no Odoo ──
    print(">>> 3/4 Atualizando list_price no Odoo...")
    atualizados = 0
    sem_odoo = 0
    currency_id = None

    if not DRY_RUN:
        cur_odoo.execute(
            "SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1"
        )
        currency_id = cur_odoo.fetchone()[0]

    for cod, info in sorted(preco_medio.items()):
        if cod not in odoo_produtos:
            sem_odoo += 1
            if VERBOSE and sem_odoo <= 10:
                print(f"  ? {cod}: nao encontrado no Odoo (sem venda)")
            continue

        produto = odoo_produtos[cod]
        preco_hist = float(info['preco'])
        preco_mediana = float(info['mediana'])
        custo = float(produto['custo'])

        # Piso: 30% sobre custo. Usa mediana se media for outlier.
        preco_final = max(preco_hist, custo * MARKUP_MINIMO) if custo > 0 else preco_hist
        if preco_mediana > 0 and abs(preco_hist - preco_mediana) / max(preco_hist, 0.01) > 0.3:
            preco_final = max(preco_mediana, custo * MARKUP_MINIMO) if custo > 0 else preco_mediana
            if VERBOSE:
                print(f"  ~ {cod}: media={preco_hist:.2f} difere da mediana={preco_mediana:.2f}, usando mediana")

        diff = abs(produto['list_price'] - preco_final)
        if produto['list_price'] > 0 and diff / max(produto['list_price'], 0.01) < 0.02:
            continue

        if not DRY_RUN:
            cur_odoo.execute("""
                UPDATE product_template
                SET list_price = %s, write_date = NOW()
                WHERE default_code = %s AND active = true
            """, (preco_final, cod))
            log_preco('venda_historico', cod, preco_final,
                      f'qtd={info["qtd"]:.0f} pedidos={info["pedidos"]} '
                      f'media={preco_hist} mediana={preco_mediana} '
                      f'custo={custo}')

        atualizados += 1
        if VERBOSE:
            margem = ((preco_final - custo) / preco_final * 100) if preco_final > 0 and custo > 0 else 0
            print(f"  ✓ {cod}: R$ {produto['list_price']:.2f} → R$ {preco_final:.2f} "
                  f"(custo=R${custo:.2f} margem={margem:.0f}% "
                  f"pedidos={info['pedidos']})")

    if not DRY_RUN:
        conn_odoo.commit()

    print(f"  Atualizados: {atualizados}")
    print(f"  Sem Odoo: {sem_odoo}")

    # Fallback para produtos sem historico: list_price = custo * markup_min
    print(">>> 3b/4 Aplicando markup minimo em produtos sem historico via SQL batch...")
    if not DRY_RUN:
        cur_odoo.execute("""
            UPDATE product_template pt
            SET list_price = ROUND(
                (SELECT (pp.standard_price->>0)::numeric * %s
                 FROM product_product pp
                 WHERE pp.product_tmpl_id = pt.id AND pp.active = true
                 LIMIT 1), 4),
                write_date = NOW()
            WHERE pt.active = true AND pt.default_code IS NOT NULL
              AND pt.list_price < (
                  SELECT (pp.standard_price->>0)::numeric * %s
                  FROM product_product pp
                  WHERE pp.product_tmpl_id = pt.id AND pp.active = true
                  LIMIT 1
              )
              AND EXISTS (
                  SELECT 1 FROM product_product pp
                  WHERE pp.product_tmpl_id = pt.id AND pp.active = true
                    AND (pp.standard_price->>0)::numeric > 0
              )
        """, (MARKUP_MINIMO, MARKUP_MINIMO))
        fallback_count = cur_odoo.rowcount
        conn_odoo.commit()
    else:
        # Estima quantos seriam afetados
        cur_odoo.execute("""
            SELECT COUNT(*) FROM product_template pt
            WHERE pt.active = true AND pt.default_code IS NOT NULL
              AND pt.list_price < (
                  SELECT (pp.standard_price->>0)::numeric * %s
                  FROM product_product pp
                  WHERE pp.product_tmpl_id = pt.id AND pp.active = true
                  LIMIT 1
              )
              AND EXISTS (
                  SELECT 1 FROM product_product pp
                  WHERE pp.product_tmpl_id = pt.id AND pp.active = true
                    AND (pp.standard_price->>0)::numeric > 0
              )
        """, (MARKUP_MINIMO,))
        fallback_count = cur_odoo.fetchone()[0]
    print(f"  Fallback (markup minimo): {fallback_count}")

    # ── Passo 4: Gerar catalogo CSV dos top 100 ──
    print(">>> 4/4 Gerando catalogo CSV dos top 100 mais vendidos...")
    top_produtos = []
    for cod, info in sorted(preco_medio.items(), key=lambda x: x[1]['pedidos'], reverse=True)[:100]:
        prod_odoo = odoo_produtos.get(cod, {})
        desc, peso = descricoes.get(cod, ('', 0))
        preco_val = float(info['preco'])
        custo_val = float(prod_odoo.get('custo', 0))
        margem = ((preco_val - custo_val) / preco_val * 100) if preco_val > 0 and custo_val > 0 else 0
        top_produtos.append({
            'codigo': cod,
            'descricao': desc or prod_odoo.get('name', ''),
            'preco_venda': preco_val,
            'custo': custo_val,
            'margem_%': round(margem, 1),
            'pedidos': info['pedidos'],
            'quantidade': float(info['qtd']),
            'peso_kg': float(peso),
        })

    os.makedirs(os.path.dirname(CATALOGO_FILE), exist_ok=True)
    with open(CATALOGO_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'codigo', 'descricao', 'preco_venda', 'custo', 'margem_%',
            'pedidos', 'quantidade', 'peso_kg'
        ])
        writer.writeheader()
        writer.writerows(top_produtos)

    print(f"  Catalogo salvo: {CATALOGO_FILE} ({len(top_produtos)} produtos)")

    cur_pdd.close()
    conn_pdd.close()
    cur_odoo.close()
    conn_odoo.close()

    elapsed = time.time() - t0
    print(f"\nTempo: {elapsed:.0f}s")
    if DRY_RUN:
        print("Use sem --dry-run para aplicar.")


if __name__ == '__main__':
    main()
