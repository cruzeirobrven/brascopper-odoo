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
    ('999', '988'): ('PVC - RECUPERADO (BRASCOPPER)', 4.00),    # =999.079 PVC RECUP legado (R$ 4,00)
    ('999', '100'): ('CORANTE P/ PE', 26.30),                   # media masters XLPE/PE (19-46)
    ('999', '090'): ('CORANTE P/ PVC', 15.78),                  # media masters PVC (10-27)
    ('999', '099'): ('MASTER XLPE-UV/TR (ANTITRACKING)', 23.41),# =999.091 MASTER CATALITICO XLPE
    ('999', '381'): ('MASTER PARA POLIETILENO PRETO', 12.00),   # ~999.410 MASTER PVC PRETO (R$ 10,62)
    ('999', '987'): ('POLIETILENO RECUPERADO', 5.00),           # ~55% do LDPE (R$ 9,26)
    ('999', '002'): ('FITA DE ALUMINIO', 15.00),                # alumínio + processamento (~AL R$ 12-14)
    ('999', '996'): ('SOMENTE MAO DE OBRA', 10.00),             # custo Mao-de-obra/kg
    ('999', '997'): ('MATERIAL S ID (PLACEHOLDER)', 0.01),      # preco simbolico
}

# Tipo de material por prefixo de codigo para estimativa via tb800
MATERIAL_CLASS = {
    'copper': {
        'codes': ['001', '191', '192', '193', '194', '195', '196', '197', '198'],
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
    # === Batch: produtos a R$ 0,01 (BOM usa 999.997) ===
    '016.107': dict(price=1.00, detail='Sem nome (estimativa generica)'),
    '026.005': dict(price=1.66, detail='CABO COPPERFIX 2,50 mm2: 2.5mm2*8.96/1000*49.48*1.15*1.3'),
    '060.188': dict(price=10.94, detail='CABO COPPERCON 11x1,50mm2: 11*1.5*8.96/1000*49.48*1.15*1.3'),
    '062.030': dict(price=7.95, detail='CABO CONTROLE COPPERFIX EPR 2x6mm2: 2*6*8.96/1000*49.48*1.15*1.3'),
    '073.248': dict(price=15.91, detail='CABO COPPERCON BFC FLEX 16x1,50mm2: 16*1.5*8.96/1000*49.48*1.15*1.3'),
    '074.641': dict(price=0.66, detail='CABO COPPERINSTRU 4x2x0,50mm2: 8*0.5*8.96/1000*49.48*1.15*1.3'),
    '080.990': dict(price=1.00, detail='Sem nome (estimativa generica)'),
    '080.991': dict(price=1.00, detail='Sem nome (estimativa generica)'),
    '085.157': dict(price=5.30, detail='CABO CopperCON SB CL2 8x1,00mm2: 8*1*8.96/1000*49.48*1.15*1.3'),
    '177.033': dict(price=2.29, detail='VEIA COPPERINSTRU 2x1,50mm2: 2*1.5*8.96/1000*49.48*1.15*1.5'),
    '177.164': dict(price=1.53, detail='GRUPO COPPERINSTRU 24x2x1,00mm2: 48*1*8.96/1000*49.48*1.15*1.5'),
    '182.098': dict(price=9.18, detail='VEIA CB CONTROLE 2x6mm2: 2*6*8.96/1000*49.48*1.15*1.5'),
    '182.162': dict(price=13.38, detail='VEIA CABO CONTROLE 7x2,50mm2: 7*2.5*8.96/1000*49.48*1.15*1.5'),
    '182.164': dict(price=9.18, detail='VEIA CABO CONTROLE FLEX FIX 2x6mm2: 2*6*8.96/1000*49.48*1.15*1.5'),
    '182.668': dict(price=18.35, detail='VEIA CONTROLE COPPERFIX BFC 16x1,50mm2: 16*1.5*8.96/1000*49.48*1.15*1.5'),
    '183.214': dict(price=0.56, detail='VEIA CABO COPPERCON 1.00mm2 (CEGA): 1*8.96/1000*49.48*1.15*1.1'),
    '183.215': dict(price=0.84, detail='VEIA CABO COPPERCON 1.50mm2 (CEGA): 1.5*8.96/1000*49.48*1.15*1.1'),
    '183.267': dict(price=0.76, detail='VEIA CABO COPPERCON 1,00mm2 CL2 GRAVADO: 1*8.96/1000*49.48*1.15*1.5'),
    '183.291': dict(price=7.65, detail='VEIA CABO COPPERCON BFC 4x2,5mm2: 4*2.5*8.96/1000*49.48*1.15*1.5'),
    '183.304': dict(price=4.59, detail='VEIA CABO COPPERCON CL2 4x1,50mm2: 4*1.5*8.96/1000*49.48*1.15*1.5'),
    '183.316': dict(price=1.59, detail='VEIA CABO COPPERCON 2.84mm2 (CEGA): 2.84*8.96/1000*49.48*1.15*1.1'),
    '183.317': dict(price=1.99, detail='VEIA CABO COPPERCON 3.54mm2 (CEGA): 3.54*8.96/1000*49.48*1.15*1.1'),
    '183.319': dict(price=0.81, detail='VEIA CABO COPPERCON 1,45mm2 (cega): 1.45*8.96/1000*49.48*1.15*1.1'),
    '183.320': dict(price=1.16, detail='VEIA CABO COPPERCON 2,07mm2 (cega): 2.07*8.96/1000*49.48*1.15*1.1'),
    '183.321': dict(price=0.90, detail='VEIA CABO COPPERCON 1,60mm2 (cega): 1.6*8.96/1000*49.48*1.15*1.1'),
    '183.322': dict(price=1.28, detail='VEIA CABO COPPERCON 2,29mm2 (cega): 2.29*8.96/1000*49.48*1.15*1.1'),
    '183.323': dict(price=0.97, detail='VEIA CABO COPPERCON 1,73mm2 (cega): 1.73*8.96/1000*49.48*1.15*1.1'),
    '183.324': dict(price=1.39, detail='VEIA CABO COPPERCON 2,47mm2 (cega): 2.47*8.96/1000*49.48*1.15*1.1'),
    '183.325': dict(price=1.22, detail='VEIA CABO COPPERCON 2,17mm2 (cega): 2.17*8.96/1000*49.48*1.15*1.1'),
    '183.326': dict(price=1.74, detail='VEIA CABO COPPERCON 3,10mm2 (cega): 3.1*8.96/1000*49.48*1.15*1.1'),
    '183.327': dict(price=1.39, detail='VEIA CABO COPPERCON 2,47mm2 (cega): 2.47*8.96/1000*49.48*1.15*1.1'),
    '183.328': dict(price=1.99, detail='VEIA CABO COPPERCON 3,54mm2 (cega): 3.54*8.96/1000*49.48*1.15*1.1'),
    '183.329': dict(price=1.59, detail='VEIA CABO COPPERCON 2,84mm2 (cega): 2.84*8.96/1000*49.48*1.15*1.1'),
    '183.330': dict(price=2.27, detail='VEIA CABO COPPERCON 4,05mm2 (cega): 4.05*8.96/1000*49.48*1.15*1.1'),
    '183.331': dict(price=1.97, detail='VEIA CABO COPPERCON 3,51mm2 (cega): 3.51*8.96/1000*49.48*1.15*1.1'),
    '183.332': dict(price=2.81, detail='VEIA CABO COPPERCON 5,01mm2 (cega): 5.01*8.96/1000*49.48*1.15*1.1'),
    '183.333': dict(price=2.53, detail='VEIA CABO COPPERCON 4,52mm2 (cega): 4.52*8.96/1000*49.48*1.15*1.1'),
    '183.334': dict(price=3.62, detail='VEIA CABO COPPERCON 6,46mm2 (cega): 6.46*8.96/1000*49.48*1.15*1.1'),
    '183.351': dict(price=3.82, detail='VEIA CABO COPPERCON CL2 2x2,50mm2: 2*2.5*8.96/1000*49.48*1.15*1.5'),
    '183.896': dict(price=18.35, detail='VEIA CABO COPPERCON CL2 4x6mm2: 4*6*8.96/1000*49.48*1.15*1.5'),
    '183.908': dict(price=3.82, detail='VEIA CABO COPPERCON 2x2,50mm2 BFA ENF.: 2*2.5*8.96/1000*49.48*1.15*1.5'),
    '183.941': dict(price=17.21, detail='VEIA CABO COPPERCON 15x1,5: 15*1.5*8.96/1000*49.48*1.15*1.5'),
    '184.017': dict(price=7.65, detail='Veia Cabo Multiplexado 10,0mm2: 10*8.96/1000*49.48*1.15*1.5'),
    '184.046': dict(price=5.74, detail='VEIA CABO COPPERFIX EPR 5x1,50mm2 ENF.: 5*1.5*8.96/1000*49.48*1.15*1.5'),
    '184.600': dict(price=4.55, detail='Veia Cabo COPPERSTEEL CAC 35mm2 Isolada: 35*6.5/1000*20*1.15'),
    '194.153': dict(price=6.56, detail='CABO COBRE 7 FIOS MD 1,53mm: 7*pi*(0.765^2)*8.96/1000*49.48*1.15'),
    '194.818': dict(price=64.72, detail='CABO COBRE 37 FIOS MD 2,09mm: 37*pi*(1.045^2)*8.96/1000*49.48*1.15'),
    '196.022': dict(price=0.72, detail='CORDA COBRE NU MOLE 22x0,285mm: 22*pi*(0.1425^2)*8.96/1000*49.48*1.15'),
    '196.132': dict(price=4.29, detail='CORDA COBRE NU MOLE 132x0,285: 132*pi*(0.1425^2)*8.96/1000*49.48*1.15'),
    '196.222': dict(price=7.22, detail='CORDA COBRE NU MOLE 222x0,285: 222*pi*(0.1425^2)*8.96/1000*49.48*1.15'),
    '196.226': dict(price=32.84, detail='CORDA COBRE NU MOLE 226x0,285mm2: 226*0.285*8.96/1000*49.48*1.15'),
    '196.510': dict(price=16.59, detail='CORDA COBRE NU MOLE 510x0,285mm: 510*pi*(0.1425^2)*8.96/1000*49.48*1.15'),
    '197.350': dict(price=18.16, detail='CORDA COBRE NU MOLE 350x0,360mm: 350*pi*(0.18^2)*8.96/1000*49.48*1.15'),
    '197.352': dict(price=18.27, detail='CORDA COBRE NU MOLE 352x0,360mm: 352*pi*(0.18^2)*8.96/1000*49.48*1.15'),
    '197.596': dict(price=30.93, detail='CORDA COBRE NU MOLE 596x0,360mm: 596*pi*(0.18^2)*8.96/1000*49.48*1.15'),
    '197.633': dict(price=32.85, detail='CORDA COBRE NU MOLE 633x0,360mm: 633*pi*(0.18^2)*8.96/1000*49.48*1.15'),
    '197.895': dict(price=139.08, detail='CORDA COBRE NU MOLE 2680x0,360: 2680*pi*(0.18^2)*8.96/1000*49.48*1.15'),
    '198.353': dict(price=72.81, detail='CORDA COBRE NU MOLE 357x0,400mm2: 357*0.4*8.96/1000*49.48*1.15'),
    '198.355': dict(price=72.60, detail='CORDA COBRE NU MOLE 356x0,400mm2: 356*0.4*8.96/1000*49.48*1.15'),
    '198.359': dict(price=101.97, detail='CORDA COBRE NU MOLE 500x0,400mm2: 500*0.4*8.96/1000*49.48*1.15'),
    '231.999': dict(price=0.04, detail='FITA DE ALUMINIO 1,2mm: pi*(0.6^2)*2.7/1000*9.68*1.15*1.2'),
    '316.107': dict(price=1.00, detail='Sem nome (estimativa generica)'),
    '193.008': dict(price=0.17, detail='FIO DE COBRE 0,652 mm: pi*(0.326^2)*8.96/1000*49.48*1.15'),
    '194.288': dict(price=23.24, detail='CABO COBRE 7 FIOS MD 2,88mm: 7*pi*(1.44^2)*8.96/1000*49.48*1.15'),
    '195.096': dict(price=10.77, detail='CABO COBRE MOLE 7 FIOS 1,96mm COMPACTADO: 7*pi*(0.98^2)*8.96/1000*49.48*1.15'),
    '198.505': dict(price=0.11, detail='CONJ. COBRE NU MOLE 7x0,200mm: 7*pi*(0.1^2)*8.96/1000*49.48*1.15'),
    '198.841': dict(price=0.02, detail='FIO DE LATAO ZF SACHS 0,200mm: 0.000279*25*1.15'),
    '999.002': dict(price=15.00, detail='FITA DE ALUMINIO (legacy_proda.presi)'),
    '999.381': dict(price=12.00, detail='MASTER PARA POLIETILENO PRETO (legacy_proda.presi)'),
    '999.987': dict(price=5.00, detail='POLIETILENO RECUPERADO (legacy_proda.presi)'),
    '999.988': dict(price=4.00, detail='PVC RECUPERADO (legacy_proda.presi)'),
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
            if abs(current - price) < 0.01:
                if VERBOSE:
                    print(f"  - {cod}: presi={current:.2f} ok (pulado)")
                continue
            else:
                if VERBOSE:
                    print(f"  ~ {cod}: presi={current:.2f} → {price:.2f} (atualizado)")

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
    print("\n>>> 2/5 Estimativa direta para produtos com BOM usando placeholder")

    fixados_parte2 = {}
    
    # Busca produtos Odoo sem preco
    cur_odoo.execute("""
        SELECT DISTINCT pt.default_code, pt.id, pt.name
        FROM product_template pt
        JOIN product_product pp ON pp.product_tmpl_id = pt.id AND pp.active = true
        WHERE pt.active = true
        AND pt.default_code IS NOT NULL AND pt.default_code != ''
        AND EXISTS (SELECT 1 FROM mrp_bom b WHERE b.product_tmpl_id = pt.id AND b.active = true)
        AND (pp.standard_price IS NULL
             OR pp.standard_price::text IN ('null', '0', '[0,1]')
             OR (pp.standard_price->>0)::numeric < 0.10)
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
                    fixados_parte2[tmpl_code] = (custo, detalhe)
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
                fixados_parte2[tmpl_code] = (custo,
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
    print("\n>>> 3/5 Recalculando BOMs via sync_custos_odoo...")
    if not DRY_RUN:
        import subprocess
        result = subprocess.run(
            ['python3', '/opt/nfelazarus/scripts/migracao/sync_custos_odoo.py'],
            capture_output=True, text=True, timeout=300
        )
        print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr[-500:])

    # ── Parte 4: Reaplicar estimativas (BOM calc sobrescreve produtos com BOM quebrada) ──
    print("\n>>> 4/5 Reaplicando estimativas (protegendo produtos com BOM quebrada)...")
    if not DRY_RUN:
        cur_odoo.execute(
            "SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1"
        )
        currency_id_4 = cur_odoo.fetchone()[0]
        reaplicados = 0
        for cod, (custo, detalhe) in sorted(fixados_parte2.items()):
            px, co = cod.split('.')
            cur_odoo.execute("""
                SELECT pt.id FROM product_template pt
                WHERE pt.default_code = %s
            """, (cod,))
            row = cur_odoo.fetchone()
            if not row:
                continue
            tmpl_id = row[0]
            json_price = json.dumps([custo, currency_id_4])
            cur_odoo.execute("""
                UPDATE product_product 
                SET standard_price = %s::jsonb, write_date = NOW()
                WHERE product_tmpl_id = %s AND active = true
            """, (json_price, tmpl_id))
            log_preco('fix_pos_bom', cod, custo, detalhe)
            reaplicados += 1
            if VERBOSE:
                print(f"  ✓ {cod}: R$ {custo:.2f} ({detalhe})")
        conn_odoo.commit()
        print(f"  Reaplicados: {reaplicados}")
    else:
        print("  (dry-run — pule reaplicacao)")

    # ── Parte 5: Precos para materiais 999.xxx sem BOM ──
    print("\n>>> 5/5 Precos de materiais 999.xxx (legacy_proda → Odoo)...")
    cur_pdd.execute("""
        SELECT pi_px, pi_co, presi FROM legacy_proda
        WHERE pi_px = '999' AND presi > 0
    """)
    precos_pdd = {f"{px}.{co}": float(presi) for px, co, presi in cur_pdd}

    if not DRY_RUN:
        cur_odoo.execute(
            "SELECT id FROM res_currency WHERE active = true ORDER BY id LIMIT 1"
        )
        currency_id = cur_odoo.fetchone()[0]
        atualizados = 0
        for cod, presi in sorted(precos_pdd.items()):
            cur_odoo.execute("""
                SELECT pt.id FROM product_template pt
                WHERE pt.default_code = %s AND pt.active = true
            """, (cod,))
            row = cur_odoo.fetchone()
            if not row:
                continue
            tmpl_id = row[0]
            cur_odoo.execute("""
                SELECT COUNT(*) FROM product_product
                WHERE product_tmpl_id = %s AND active = true
                  AND (standard_price IS NULL
                       OR standard_price::text IN ('null', '0', '[0,1]')
                       OR (standard_price->>0)::numeric < 0.10)
            """, (tmpl_id,))
            need_update = cur_odoo.fetchone()[0]
            if need_update == 0:
                continue
            json_price = json.dumps([presi, currency_id])
            cur_odoo.execute("""
                UPDATE product_product
                SET standard_price = %s::jsonb, write_date = NOW()
                WHERE product_tmpl_id = %s AND active = true
            """, (json_price, tmpl_id))
            log_preco('fix_legacy_raw', cod, presi, f'legacy_proda.presi = {presi}')
            atualizados += 1
            if VERBOSE:
                print(f"  ✓ {cod}: R$ {presi:.2f}")
        conn_odoo.commit()
        print(f"  Materiais 999.xxx atualizados: {atualizados}")
    else:
        print(f"  Materiais 999.xxx com presi: {len(precos_pdd)} (dry-run)")

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
