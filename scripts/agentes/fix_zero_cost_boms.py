#!/usr/bin/env python3
"""
Corrige os 95 produtos com BOM que ainda estao com custo zero.

Estrategia:
  1. Insere precos estimados no legacy_proda para materiais 999.xxx sem preco
     (PVC Recuperado, Corantes, Master PE, Fita Aluminio, etc.)
  2. Para produtos cuja BOM usa placeholder 999.997 (sem componentes reais),
     estima custo diretamente via tb800 (peso cadastrado) x preco/kg + markup.

Uso: python3 fix_zero_cost_boms.py [--dry-run] [--verbose]
"""
import sys, json, time, os
from datetime import date, datetime
import psycopg2

LOG_FILE = '/opt/nfelazarus/logs/historico_precos.jsonl'

PDD_PG = dict(host='localhost', user='brasc1', password='mara5534', dbname='brascopper_pdd')
ODOO_PG = dict(host='100.119.223.92', user='postgres', password='MULETA', dbname='odoo18')
NFEHUB_PG = dict(host='localhost', user='nfehub', password='nfehub123', dbname='nfehub')

DRY_RUN = '--dry-run' in sys.argv
VERBOSE = '--verbose' in sys.argv

TODAY = date.today()
MARKUP = 1.15

# Precos estimados para materiais 999.xxx sem cotacao no legado
# Fonte: estimativa baseada em materiais similares + conversa com usuario
ESTIMATED_PRICES = {
    ('999', '988'): ('PVC - RECUPERADO (BRASCOPPER)', 4.44),   # 60% do PVC virgem (7.40)
    ('999', '100'): ('CORANTE P/ PE', 20.00),                   # similar a master PVC (~18-25)
    ('999', '090'): ('CORANTE P/ PVC', 20.00),                  # idem
    ('999', '099'): ('MASTER XLPE-UV/TR (ANTITRACKING)', 28.71),# similar 999.091
    ('999', '381'): ('MASTER PARA POLIETILENO PRETO', 17.00),   # similar 999.410 PVC PRETO
    ('999', '987'): ('POLIETILENO RECUPERADO', 4.00),           # 60% do PE virgem (6.68)
    ('999', '002'): ('FITA DE ALUMINIO', 15.00),                # aluminio + processamento
    ('999', '996'): ('SOMENTE MAO DE OBRA', 10.00),             # custo Mao-de-obra/kg
    ('999', '997'): ('MATERIAL S ID (PLACEHOLDER)', 0.01),      # preco simbolico
}

# Tipo de material por prefixo de codigo para estimativa via tb800
MATERIAL_CLASS = {
    'copper': {
        'codes': ['191', '192', '193', '194', '195', '196', '197', '198'],
        'price_kg': 49.48,  # cobre
    },
    'steel': {
        'codes': ['279', '280', '291'],
        'price_kg': 14.50,  # aco galvanizado
    },
    'aluminum': {
        'codes': ['289', '299', '300'],
        'price_kg': 9.68,  # aluminio
    },
    'copper_cable': {
        'codes': ['016', '020', '026', '032', '053', '055', '060', '062', '063',
                   '067', '070', '073', '074', '075', '080', '085', '090', '151',
                   '172', '316'],
        'price_kg': 35.00,  # cabo de cobre (media ponderada cobre + isolantes)
    },
    'aluminum_cable': {
        'codes': ['231', '259'],
        'price_kg': 12.00,  # cabo de aluminio (aluminio + isolantes)
    },
    'instrument_veia': {
        'codes': ['177', '182', '183', '184', '187'],
        'price_kg': 30.00,  # veia de instrumentacao (cobre + isolante)
    },
    'raw_material': {
        'codes': ['999'],
        'price_kg': 10.00,  # default para materiais 999.xxx sem classificacao
    },
}

# Estimativas diretas para produtos com BOM quebrada (codigos .001/.004/.006/.007/.863)
# Calculado: peso_cobre_kgm = n_condutores * secao_mm2 * 8.96 / 1000 * multiplicador_isolante
DIRECT_ESTIMATES = {
    '053.008': dict(price=3.00, detail='VEIA TIC COPPEFIX XLPE (estimativa generica)'),
    '067.031': dict(price=9.38, detail='CABO COPPERFIX XLPE 2x10mm2: (2*10*8.96/1000)*1.3*35*1.15'),
    '177.089': dict(price=1.86, detail='GRUPO COPPERINSTRU 4x2x0,50mm2: (8*0.5*8.96/1000)*1.5*30*1.15'),
    '177.174': dict(price=0.93, detail='Grupo CopperINSTRU 2x2x0,50mm2: (4*0.5*8.96/1000)*1.5*30*1.15'),
    '177.920': dict(price=1.86, detail='GRUPO COPPERINSTRU 4x2x0,50mm2 ENF: (8*0.5*8.96/1000)*1.5*30*1.15'),
    '177.999': dict(price=0.46, detail='VEIA COPPERINSTRU 2x0,50mm2: (2*0.5*8.96/1000)*1.5*30*1.15'),
    '184.044': dict(price=4.06, detail='VEIA CABO COPPERFIX EPR 5x1,50mm2: (5*1.5*8.96/1000)*1.5*35*1.15'),
    '184.052': dict(price=18.76, detail='VEIA CABO COPPERFIX EPR 4x10,0mm2: (4*10*8.96/1000)*1.3*35*1.15'),
    '184.063': dict(price=6.52, detail='VEIA CABO COPPERFIX EPR 3x4,00mm2: (3*4*8.96/1000)*1.5*35*1.15'),
    '184.073': dict(price=26.00, detail='VEIA CABO COPPERFIX EPR 12x4,00: (12*4*8.96/1000)*1.5*35*1.15'),
    '193.220': dict(price=1.94, detail='FIO COBRE ESTANHADO 2,20mm: pi*(1.1^2)*8.96/1000*49.48*1.15'),
    '195.326': dict(price=0.50, detail='CORDA COBRE NU 16x0,278: 16*pi*(0.139^2)*8.96/1000*49.48*1.15'),
    '197.064': dict(price=11.73, detail='CORDA COBRE NU 64x0,360mm2: 64*0.36*8.96/1000*49.48*1.15'),
    '198.202': dict(price=7.46, detail='CORDA COBRE NU 467x0,200mm: 467*pi*(0.1^2)*8.96/1000*49.48*1.15'),
    '198.842': dict(price=0.37, detail='CORDA COBRE NU 12x0,278mm: 12*pi*(0.139^2)*8.96/1000*49.48*1.15'),
    '198.844': dict(price=0.25, detail='CORDA COBRE NU 8x0,278mm: 8*pi*(0.139^2)*8.96/1000*49.48*1.15'),
    '203.006': dict(price=20.00, detail='BOM: 203.005 x1 a R$20'),
    '177.088': dict(price=1.86, detail='GRUPO COPPERINSTRU 4x2x0,50mm2 (igual 177.089)'),
    '177.920': dict(price=1.86, detail='GRUPO COPPERINSTRU 4x2x0,50mm2 ENF. (igual 177.089)'),
}


def get_material_price_kg(code):
    """Determina o preco por kg estimado para um produto baseado no codigo."""
    prefix = code.split('.')[0]
    for tipo, info in MATERIAL_CLASS.items():
        if prefix in info['codes']:
            return info['price_kg']
    return None


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
    print(f"{'DRY RUN - ' if DRY_RUN else ''}Fix Produtos BOM sem Custo")
    print("=" * 50)

    conn_pdd = psycopg2.connect(**PDD_PG)
    cur_pdd = conn_pdd.cursor()
    conn_odoo = psycopg2.connect(**ODOO_PG)
    cur_odoo = conn_odoo.cursor()
    conn_nfe = psycopg2.connect(**NFEHUB_PG)
    cur_nfe = conn_nfe.cursor()

    # ── Parte 1: Inserir precos estimados no legacy_proda ──
    print("\n>>> 1/3 Precos estimados para materiais 999.xxx faltantes")
    insert_count = 0
    for (px, co), (descr, price) in sorted(ESTIMATED_PRICES.items()):
        cod = f'{px}.{co}'
        # Verifica se ja existe em legacy_proda
        cur_pdd.execute(
            "SELECT presi FROM legacy_proda WHERE pi_px = %s AND pi_co = %s",
            (px, co)
        )
        row = cur_pdd.fetchone()
        current = float(row[0]) if row else 0

        if current > 0 and cod != '999.997':
            if VERBOSE:
                print(f"  - {cod}: ja tem presi={current:.2f} (pulado)")
            continue

        if not DRY_RUN:
            if row:
                cur_pdd.execute(
                    "UPDATE legacy_proda SET presi = %s, prdat = %s "
                    "WHERE pi_px = %s AND pi_co = %s",
                    (price, TODAY, px, co)
                )
            else:
                cur_pdd.execute(
                    "INSERT INTO legacy_proda (pi_px, pi_co, itdesc, presi, prdat) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (px, co, descr, price, TODAY)
                )
            log_preco('estimado_material', cod, price,
                      f'Preco estimado (sem cotacao no legado)')
        insert_count += 1
        if VERBOSE:
            print(f"  ✓ {cod}: presi = R$ {price:.2f} ({descr})")

    if not DRY_RUN:
        conn_pdd.commit()
    print(f"  Total inseridos/atualizados: {insert_count}")

    # ── Parte 2: Estimar produtos com placeholder 999.997 ou BOM quebrada ──
    print("\n>>> 2/3 Estimativa direta para produtos com BOM usando placeholder")
    
    # Busca produtos Odoo sem preco
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
    zero_products = list(cur_odoo.fetchall())
    print(f"  Produtos zero a processar: {len(zero_products)}")

    cur_odoo.execute(
        "SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1"
    )
    currency_id = cur_odoo.fetchone()[0]

    estimados = 0
    sem_dados = 0
    erros = 0

    for tmpl_code, tmpl_id, tmpl_name in zero_products:
        px, co = tmpl_code.split('.')

        # Tenta peso via ItemTecnicoFamilia.tb800 (g/m)
        peso_kg = None
        try:
            from producao.models import ItemTecnicoFamilia
            fam = ItemTecnicoFamilia.objects.filter(it_px=px, it_co=co).first()
            if fam and fam.tb800 and float(fam.tb800) > 0:
                peso_kg = float(fam.tb800) / 1000  # g/m → kg/m
        except Exception:
            pass

        # Fallback: legacy_proda.prokg (ignora placeholder 0.001)
        if not peso_kg or peso_kg <= 0:
            cur_pdd.execute(
                "SELECT prokg FROM legacy_proda WHERE pi_px=%s AND pi_co=%s",
                (px, co)
            )
            row = cur_pdd.fetchone()
            if row and row[0] and float(row[0]) > 0.001:
                peso_kg = float(row[0])

        # Ainda sem peso? Tenta erp_catalogo_tecnico
        if not peso_kg or peso_kg <= 0:
            cur_nfe.execute(
                "SELECT peso_kg FROM erp_catalogo_tecnico WHERE pi_px=%s AND pi_co=%s",
                (px, co)
            )
            row = cur_nfe.fetchone()
            if row and row[0] and float(row[0]) > 0.001:
                peso_kg = float(row[0])

        # Fallback: estimativa direta para produtos com BOM quebrada
        if (not peso_kg or peso_kg <= 0) and tmpl_code in DIRECT_ESTIMATES:
            custo = DIRECT_ESTIMATES[tmpl_code]['price']
            detalhe = DIRECT_ESTIMATES[tmpl_code]['detail']
            try:
                if not DRY_RUN:
                    json_price = json.dumps([custo, currency_id])
                    cur_odoo.execute("""
                        UPDATE product_product 
                        SET standard_price = %s::jsonb, write_date = NOW()
                        WHERE product_tmpl_id = %s AND active = true
                    """, (json_price, tmpl_id))
                    log_preco('fix_direta', tmpl_code, custo, detalhe)
                estimados += 1
                if VERBOSE:
                    print(f"  ✓ R$ {custo:.4f}  {tmpl_code}  ({detalhe})")
            except Exception as e:
                erros += 1
                print(f"  ERRO {tmpl_code}: {e}")
            continue

        if not peso_kg or peso_kg <= 0:
            sem_dados += 1
            if VERBOSE:
                print(f"  ? {tmpl_code}: sem peso cadastrado")
            continue

        price_kg = get_material_price_kg(tmpl_code)
        if not price_kg:
            sem_dados += 1
            if VERBOSE:
                print(f"  ? {tmpl_code}: tipo de material nao reconhecido")
            continue

        custo = round(peso_kg * price_kg * MARKUP, 4)

        try:
            if not DRY_RUN:
                json_price = json.dumps([custo, currency_id])
                cur_odoo.execute("""
                    UPDATE product_product 
                    SET standard_price = %s::jsonb, write_date = NOW()
                    WHERE product_tmpl_id = %s AND active = true
                """, (json_price, tmpl_id))
                log_preco('fix_tb800', tmpl_code, custo,
                          f'tb800={peso_kg*1000:.0f}g/m x R${price_kg}/kg x {MARKUP}')
            estimados += 1
            if VERBOSE:
                print(f"  ✓ R$ {custo:.4f}  {tmpl_code}  ({peso_kg*1000:.0f}g/m x R${price_kg})")
        except Exception as e:
            erros += 1
            print(f"  ERRO {tmpl_code}: {e}")

        if not DRY_RUN and estimados % 50 == 0:
            conn_odoo.commit()

    if not DRY_RUN:
        conn_odoo.commit()

    print(f"  Estimados via tb800: {estimados}")
    print(f"  Sem dados de peso: {sem_dados}")
    print(f"  Erros: {erros}")

    # ── Parte 3: Recalcular BOMs via sync_custos_odoo ──
    print("\n>>> 3/3 Recalculando BOMs via sync_custos_odoo...")
    if not DRY_RUN:
        import subprocess
        result = subprocess.run(
            ['python3', '/opt/nfelazarus/scripts/migracao/sync_custos_odoo.py'],
            capture_output=True, text=True, timeout=300
        )
        print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-500:])

    # ── Parte 4: Reaplicar estimativas diretas (BOM calc sobrescreve com BOM quebrada) ──
    print("\n>>> 4/4 Reaplicando estimativas diretas (protegendo BOMs quebradas)...")
    if not DRY_RUN:
        cur_odoo.execute(
            "SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1"
        )
        currency_id_4 = cur_odoo.fetchone()[0]
        reaplicados = 0
        for cod, info in sorted(DIRECT_ESTIMATES.items()):
            px, co = cod.split('.')
            cur_odoo.execute("""
                SELECT pt.id FROM product_template pt
                WHERE pt.default_code = %s
            """, (cod,))
            row = cur_odoo.fetchone()
            if not row:
                continue
            tmpl_id = row[0]
            custo = info['price']
            detalhe = info['detail']
            json_price = json.dumps([custo, currency_id_4])
            cur_odoo.execute("""
                UPDATE product_product 
                SET standard_price = %s::jsonb, write_date = NOW()
                WHERE product_tmpl_id = %s AND active = true
            """, (json_price, tmpl_id))
            log_preco('fix_direta_after_bom', cod, custo, detalhe)
            reaplicados += 1
            if VERBOSE:
                print(f"  ✓ {cod}: R$ {custo:.2f} ({detalhe})")
        conn_odoo.commit()
        print(f"  Reaplicados: {reaplicados}")
    else:
        print("  (dry-run — pule reaplicacao)")

    elapsed = time.time() - t0
    print()
    print("=" * 50)
    print(f"Tempo: {elapsed:.0f}s")
    if DRY_RUN:
        print("\nUse sem --dry-run para aplicar.")

    cur_pdd.close()
    conn_pdd.close()
    cur_nfe.close()
    conn_nfe.close()
    cur_odoo.close()
    conn_odoo.close()


if __name__ == '__main__':
    import os as _os
    _os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brascopper_pdd.settings')
    import django; django.setup()
    main()
